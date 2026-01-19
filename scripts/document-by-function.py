"""Document Python files by extracting functions first, then describing each.

Uses AST for deterministic structure extraction, LLM only for descriptions.
Supports hash-based caching to skip unchanged functions.
Uses concurrent processing to keep multiple LLM requests in flight.
"""
import sys
import ast
import os
import json
import hashlib
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add src to path for gateway import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Thread-safe print lock
_print_lock = threading.Lock()

CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_FILE = CACHE_DIR / "function_docs.json"


def load_cache():
    """Load cached function descriptions."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save function descriptions cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)


def hash_code(code: str) -> str:
    """Generate short hash of code for change detection."""
    return hashlib.md5(code.encode()).hexdigest()[:8]


def extract_functions(filepath):
    """Use AST to extract all functions/classes with exact line numbers."""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    tree = ast.parse(content)
    lines = content.split('\n')

    results = []

    # Get module docstring if present
    docstring = ast.get_docstring(tree)
    if docstring:
        results.append({
            'name': 'module_docstring',
            'type': 'global',
            'start': 1,
            'end': 1,
            'code': docstring
        })

    # Get top-level imports
    import_lines = []
    import_code = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_lines.append(node.lineno)
            import_code.append(lines[node.lineno - 1])

    if import_lines:
        results.append({
            'name': 'imports',
            'type': 'import-block',
            'start': min(import_lines),
            'end': max(import_lines),
            'code': '\n'.join(import_code)
        })

    # Get functions and classes
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno
            end = node.end_lineno
            name = node.name
            node_type = 'class' if isinstance(node, ast.ClassDef) else 'function'

            code_lines = lines[start-1:end]
            code = '\n'.join(code_lines)

            results.append({
                'name': name,
                'type': node_type,
                'start': start,
                'end': end,
                'code': code
            })

    # Get top-level assignments (constants, app = typer.Typer(), etc)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    code = '\n'.join(lines[node.lineno-1:node.end_lineno])
                    results.append({
                        'name': target.id,
                        'type': 'constant',
                        'start': node.lineno,
                        'end': node.end_lineno,
                        'code': code
                    })

    results.sort(key=lambda x: x['start'])
    return results


def call_llm(prompt):
    """Call LLM via project's gateway (handles model loading).

    Returns: (response, llm_time_seconds)
    """
    import time
    from gateway import get_gateway

    t0 = time.time()
    try:
        gateway = get_gateway()
        response = gateway.request_text(prompt)
        llm_time = time.time() - t0
        return response, llm_time
    except Exception as e:
        llm_time = time.time() - t0
        return f"Error: {e}", llm_time


def estimate_tokens(text: str) -> int:
    """Estimate token count (roughly 4 chars per token)."""
    return len(text) // 4


def extract_nested_functions(code: str, parent_name: str) -> list:
    """Extract nested functions/methods from a class or large function."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    lines = code.split('\n')
    results = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip the parent function itself (it's at line 1 of the snippet)
            if node.lineno == 1 and node.name == parent_name.split('.')[-1]:
                continue

            start = node.lineno
            end = node.end_lineno
            code_lines = lines[start-1:end]
            nested_code = '\n'.join(code_lines)

            results.append({
                'name': f"{parent_name}.{node.name}",
                'type': 'method' if parent_name else 'function',
                'start': start,  # Relative to parent
                'end': end,
                'code': nested_code
            })

    return results


def describe_function(func, max_tokens=5000):
    """Get LLM to describe a single function using sandwich prompt structure.

    Returns: (description, timing_info)
        timing_info = {'llm_time': seconds, 'tokens_in': int, 'nested_calls': int}
    """
    code = func['code']
    tokens = estimate_tokens(code)
    timing_info = {'llm_time': 0.0, 'tokens_in': tokens, 'nested_calls': 0}

    # If too large, extract and describe nested functions separately
    if tokens > max_tokens and func['type'] in ('class', 'function'):
        nested = extract_nested_functions(code, func['name'])
        if nested:
            # Describe nested items individually
            nested_descs = []
            total_nested_time = 0.0
            for nf in nested[:10]:  # Limit to avoid runaway
                nested_desc, nested_timing = describe_function(nf, max_tokens)
                total_nested_time += nested_timing['llm_time']
                nested_descs.append(f"  - {nf['name']}: {nested_desc}")

            timing_info['llm_time'] = total_nested_time
            timing_info['nested_calls'] = len(nested)
            # Summary for parent
            return f"Contains {len(nested)} methods: " + "; ".join([n['name'].split('.')[-1] for n in nested[:5]]), timing_info

    # Truncate code for prompt if still too long
    code_for_prompt = code[:8000] if len(code) > 8000 else code

    # Sandwich prompt: Role -> Task -> Rules -> Content -> Example -> Output instruction
    prompt = f"""You are a code documentation specialist creating concise function summaries.

TASK: Write ONE sentence describing what this Python {func['type']} does.

RULES:
1. Start with a verb (Parses, Returns, Validates, Creates, Handles)
2. Be specific about behavior, not just signature
3. No filler ("This function", "basically", "essentially")
4. Mention key parameters only if they affect meaning

=== BEGIN CODE ===
{code_for_prompt}
=== END CODE ===

EXAMPLE FORMAT (do NOT copy - reference only):
"Parses interval strings like '5m' or '1h' into seconds, returning None on invalid input."

ONE SENTENCE (start with verb):"""

    response, llm_time = call_llm(prompt)
    timing_info['llm_time'] = llm_time

    # Take first sentence only, clean up
    desc = response.strip().split('\n')[0].strip()
    # Remove common filler starts
    for prefix in ['This ', 'The ', 'A ', 'An ']:
        if desc.startswith(prefix):
            desc = desc[len(prefix):]
            break
    # Ensure starts with capital
    if desc and desc[0].islower():
        desc = desc[0].upper() + desc[1:]
    return desc, timing_info


def process_file(filepath, cache, force=False):
    """Process a single file, using cache where possible."""
    filepath = str(Path(filepath).resolve())

    print(f"Extracting functions from {filepath}...")
    functions = extract_functions(filepath)
    print(f"Found {len(functions)} items")

    file_cache = cache.get(filepath, {})
    results = []
    stats = {'cached': 0, 'new': 0, 'changed': 0}

    for i, func in enumerate(functions):
        code_hash = hash_code(func['code'])
        cached_entry = file_cache.get(func['name'], {})
        cached_hash = cached_entry.get('hash', '')
        cached_desc = cached_entry.get('description', '')

        # Determine status
        if force:
            status = 'FORCED'
            need_llm = True
        elif not cached_hash:
            status = 'NEW'
            need_llm = True
            stats['new'] += 1
        elif cached_hash != code_hash:
            status = 'CHANGED'
            need_llm = True
            stats['changed'] += 1
        else:
            status = 'cached'
            need_llm = False
            stats['cached'] += 1

        print(f"  [{i+1}/{len(functions)}] {func['type']}: {func['name']} ({status})...", end='', flush=True)

        # Get description
        if need_llm:
            if func['type'] == 'import-block':
                desc = "Module imports"
            elif func['type'] == 'global' and func['name'] == 'module_docstring':
                desc = "Module docstring"
            else:
                desc, timing_info = describe_function(func)
        else:
            desc = cached_desc

        # Update cache
        file_cache[func['name']] = {
            'hash': code_hash,
            'description': desc,
            'start': func['start'],
            'end': func['end'],
            'type': func['type']
        }

        results.append({
            'start': func['start'],
            'end': func['end'],
            'type': func['type'],
            'name': func['name'],
            'hash': code_hash,
            'status': status,
            'description': desc
        })
        print(f" done")

    # Update cache
    cache[filepath] = file_cache

    return results, stats


def find_python_files(directory, exclude_patterns=None):
    """Recursively find all Python files in directory."""
    exclude_patterns = exclude_patterns or ['.venv', 'venv', '__pycache__', '.git', 'build', 'htmlcov', 'archive', '.auto-claude']
    py_files = []

    for root, dirs, files in os.walk(directory):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_patterns]

        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))

    return sorted(py_files)


def generate_overview(all_results, directory):
    """Generate system architecture overview from all file documentation."""
    # Collect data for overview
    files_data = []
    total_functions = 0
    total_classes = 0
    total_lines = 0

    for filepath, results in all_results.items():
        rel_path = os.path.relpath(filepath, directory)
        functions = [r for r in results if r['type'] == 'function']
        classes = [r for r in results if r['type'] == 'class']
        max_line = max(r['end'] for r in results) if results else 0

        # Extract imports to understand dependencies
        imports = [r for r in results if r['type'] == 'import-block']

        files_data.append({
            'path': rel_path,
            'functions': functions,
            'classes': classes,
            'line_count': max_line,
            'imports': imports
        })

        total_functions += len(functions)
        total_classes += len(classes)
        total_lines += max_line

    # Build overview prompt
    file_summaries = []
    for fd in files_data:
        func_names = [f['name'] for f in fd['functions'][:10]]
        class_names = [c['name'] for c in fd['classes']]
        summary = f"- **{fd['path']}** ({fd['line_count']} lines): "
        if class_names:
            summary += f"Classes: {', '.join(class_names)}. "
        if func_names:
            summary += f"Functions: {', '.join(func_names[:5])}"
            if len(func_names) > 5:
                summary += f" (+{len(func_names)-5} more)"
        file_summaries.append(summary)

    overview_prompt = f"""You are a software architect creating a system overview document.

TASK: Create a concise architecture overview for this Python project.

PROJECT STATS:
- {len(files_data)} Python files
- {total_functions} functions
- {total_classes} classes
- ~{total_lines} total lines

FILE SUMMARIES:
{chr(10).join(file_summaries)}

Create a brief architecture overview with these sections:
1. **Purpose**: What does this project do? (1-2 sentences)
2. **Key Modules**: List 3-5 most important files and their roles
3. **Entry Points**: Where does execution start?
4. **Data Flow**: How do the main components interact?

Keep it under 300 words. Be specific to THIS codebase."""

    overview = call_llm(overview_prompt)
    return overview, {
        'files': len(files_data),
        'functions': total_functions,
        'classes': total_classes,
        'lines': total_lines
    }


def process_directory(directory, cache, force=False, output_file=None, workers=10, verbose=False, timing_log=None):
    """Process all Python files in a directory with concurrent LLM calls."""
    import time
    total_start = time.time()
    timing_entries = []  # For detailed timing log

    py_files = find_python_files(directory)
    print(f"Found {len(py_files)} Python files in {directory}")

    # Phase 1: Extract all functions from all files (fast, no LLM)
    print("\n=== Phase 1: Extracting functions (AST) ===")
    all_extractions = {}  # filepath -> list of functions
    for i, filepath in enumerate(py_files):
        rel_path = os.path.relpath(filepath, directory)
        try:
            functions = extract_functions(filepath)
            all_extractions[filepath] = functions
            print(f"  [{i+1}/{len(py_files)}] {rel_path}: {len(functions)} items")
        except Exception as e:
            print(f"  [{i+1}/{len(py_files)}] {rel_path}: ERROR - {e}")
            all_extractions[filepath] = []

    # Phase 2: Build work queue (items needing LLM)
    print("\n=== Phase 2: Building work queue ===")
    work_queue = []  # list of (filepath, func, code_hash, cached_desc)
    total_stats = {'cached': 0, 'new': 0, 'changed': 0}

    for filepath, functions in all_extractions.items():
        file_cache = cache.get(str(Path(filepath).resolve()), {})
        for func in functions:
            code_hash = hash_code(func['code'])
            cached_entry = file_cache.get(func['name'], {})
            cached_hash = cached_entry.get('hash', '')
            cached_desc = cached_entry.get('description', '')

            if func['type'] == 'import-block':
                func['_description'] = "Module imports"
                func['_status'] = 'skip'
                total_stats['cached'] += 1
            elif func['type'] == 'global' and func['name'] == 'module_docstring':
                func['_description'] = "Module docstring"
                func['_status'] = 'skip'
                total_stats['cached'] += 1
            elif not force and cached_hash == code_hash and cached_desc:
                func['_description'] = cached_desc
                func['_status'] = 'cached'
                total_stats['cached'] += 1
            else:
                status = 'FORCED' if force else ('CHANGED' if cached_hash else 'NEW')
                func['_status'] = status
                func['_hash'] = code_hash
                work_queue.append((filepath, func))
                if status == 'NEW':
                    total_stats['new'] += 1
                elif status == 'CHANGED':
                    total_stats['changed'] += 1

    print(f"  {len(work_queue)} items need LLM, {total_stats['cached']} cached")

    # Phase 3: Fixed queue level - add one when one completes
    if work_queue:
        import time
        total = len(work_queue)
        completed = 0
        queue_size = workers
        work_iter = iter(work_queue)
        pending = {}  # future -> (filepath, func, start_time)
        timing_data = []  # (filepath, func_name, duration)
        phase3_start = time.time()

        print(f"\n=== Phase 3: LLM (queue={queue_size}, total={total}) ===", flush=True)

        def process_item(item):
            """Returns (filepath, func, desc, timing_info)"""
            import time as t
            t0 = t.time()
            filepath, func = item
            desc, timing_info = describe_function(func)
            timing_info['total_time'] = t.time() - t0  # wall clock including overhead
            return filepath, func, desc, timing_info

        with ThreadPoolExecutor(max_workers=queue_size) as executor:
            # Fill queue to target level
            for _ in range(min(queue_size, total)):
                try:
                    item = next(work_iter)
                    future = executor.submit(process_item, item)
                    pending[future] = (item[0], item[1], time.time())
                except StopIteration:
                    break

            # Process: when one completes, add one
            total_tokens = 0
            total_llm_time = 0.0
            errors = 0
            while pending:
                done = next(as_completed(pending.keys()))
                filepath_orig, func_orig, start_time = pending.pop(done)
                try:
                    filepath, func, desc, timing_info = done.result()
                    is_error = desc.startswith('Error:')
                    if is_error:
                        errors += 1
                except Exception as e:
                    filepath, func = filepath_orig, func_orig
                    desc = f"Error: {e}"
                    timing_info = {'llm_time': 0, 'tokens_in': 0, 'total_time': 0}
                    is_error = True
                    errors += 1

                wall_time = time.time() - start_time
                tokens = timing_info['tokens_in']
                llm_time = timing_info['llm_time']
                total_tokens += tokens
                total_llm_time += llm_time
                func['_description'] = desc
                completed += 1
                timing_data.append((filepath, func['name'], wall_time, tokens, llm_time, is_error))

                if verbose:
                    err_flag = " ERR" if is_error else ""
                    print(f"  [{completed}/{total}] wall={wall_time:.2f}s llm={llm_time:.2f}s {tokens:>5}tok {os.path.relpath(filepath, directory)}:{func['name']}{err_flag}", flush=True)
                else:
                    # Brief progress indicator
                    print(f"\r  Processing: {completed}/{total} ({total_tokens} tokens, {errors} errors)", end='', flush=True)

                # Add one to maintain queue level
                try:
                    item = next(work_iter)
                    future = executor.submit(process_item, item)
                    pending[future] = (item[0], item[1], time.time())
                except StopIteration:
                    pass

        phase3_duration = time.time() - phase3_start
        if not verbose:
            print()  # Newline after progress indicator
        print(f"\n  Phase 3 complete:", flush=True)
        print(f"    Wall time: {phase3_duration:.1f}s total, {phase3_duration/total:.2f}s avg per item", flush=True)
        print(f"    LLM time:  {total_llm_time:.1f}s total, {total_llm_time/total:.2f}s avg per item", flush=True)
        print(f"    Tokens:    {total_tokens} ({total_tokens/phase3_duration:.0f} tok/s wall, {total_tokens/total_llm_time:.0f} tok/s LLM)" if total_llm_time > 0 else f"    Tokens: {total_tokens}", flush=True)
        print(f"    Errors:    {errors}", flush=True)

        # Write detailed timing log if requested
        if timing_log:
            from datetime import datetime
            with open(timing_log, 'w', encoding='utf-8') as f:
                f.write(f"# Timing Log\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"## Summary\n\n")
                f.write(f"- Wall time: {phase3_duration:.1f}s\n")
                f.write(f"- LLM time: {total_llm_time:.1f}s\n")
                f.write(f"- Items processed: {total}\n")
                f.write(f"- Total tokens: {total_tokens}\n")
                f.write(f"- Errors: {errors}\n")
                f.write(f"- Avg wall time per item: {phase3_duration/total:.2f}s\n")
                f.write(f"- Avg LLM time per item: {total_llm_time/total:.2f}s\n")
                if total_llm_time > 0:
                    f.write(f"- Throughput: {total_tokens/total_llm_time:.0f} tok/s (LLM), {total_tokens/phase3_duration:.0f} tok/s (wall)\n")
                f.write(f"\n## Per-Function Timing\n\n")
                f.write(f"| File | Function | Wall (s) | LLM (s) | Tokens | Error |\n")
                f.write(f"|------|----------|----------|---------|--------|-------|\n")
                for fpath, fname, wall, tokens, llm, is_err in timing_data:
                    rel = os.path.relpath(fpath, directory)
                    err_mark = "ERR" if is_err else ""
                    f.write(f"| {rel} | {fname} | {wall:.2f} | {llm:.2f} | {tokens} | {err_mark} |\n")

                # Per-file summary
                f.write(f"\n## Per-File Summary\n\n")
                file_stats = {}  # rel_path -> {wall, llm, tokens, count, errors}
                for fpath, fname, wall, tokens, llm, is_err in timing_data:
                    rel = os.path.relpath(fpath, directory)
                    if rel not in file_stats:
                        file_stats[rel] = {'wall': 0, 'llm': 0, 'tokens': 0, 'count': 0, 'errors': 0}
                    file_stats[rel]['wall'] += wall
                    file_stats[rel]['llm'] += llm
                    file_stats[rel]['tokens'] += tokens
                    file_stats[rel]['count'] += 1
                    if is_err:
                        file_stats[rel]['errors'] += 1
                f.write(f"| File | Functions | Wall (s) | LLM (s) | Tokens | Errors |\n")
                f.write(f"|------|-----------|----------|---------|--------|--------|\n")
                for fpath in sorted(file_stats.keys(), key=lambda x: -file_stats[x]['wall']):
                    s = file_stats[fpath]
                    f.write(f"| {fpath} | {s['count']} | {s['wall']:.1f} | {s['llm']:.1f} | {s['tokens']} | {s['errors']} |\n")
            print(f"  Timing log written to {timing_log}")

        # Store timing for output
        total_stats['timing'] = timing_data
        total_stats['phase3_duration'] = phase3_duration

    # Phase 4: Assemble results and update cache
    print("\n=== Phase 4: Assembling results ===")
    all_results = {}
    for filepath, functions in all_extractions.items():
        filepath_resolved = str(Path(filepath).resolve())
        file_cache = cache.get(filepath_resolved, {})
        results = []

        for func in functions:
            code_hash = func.get('_hash', hash_code(func['code']))
            desc = func.get('_description', '')
            status = func.get('_status', 'unknown')

            # Update cache
            file_cache[func['name']] = {
                'hash': code_hash,
                'description': desc,
                'start': func['start'],
                'end': func['end'],
                'type': func['type']
            }

            results.append({
                'start': func['start'],
                'end': func['end'],
                'type': func['type'],
                'name': func['name'],
                'hash': code_hash,
                'status': status,
                'description': desc
            })

        cache[filepath_resolved] = file_cache
        all_results[filepath] = results

    save_cache(cache)

    # Generate overview
    print("\n=== Generating System Overview ===")
    overview, project_stats = generate_overview(all_results, directory)

    # Write output
    if output_file:
        from datetime import datetime
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Project Documentation\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Stats:** {project_stats['files']} files, {project_stats['functions']} functions, ")
            f.write(f"{project_stats['classes']} classes, ~{project_stats['lines']} lines\n\n")
            f.write(f"**Cache:** {total_stats['cached']} cached, {total_stats['new']} new, {total_stats['changed']} changed\n\n")
            if 'phase3_duration' in total_stats:
                f.write(f"**Timing:** {total_stats['phase3_duration']:.1f}s total LLM time")
                if total_stats.get('timing'):
                    avg = total_stats['phase3_duration'] / len(total_stats['timing'])
                    f.write(f", {avg:.2f}s avg per function\n\n")
                else:
                    f.write("\n\n")
            f.write(f"---\n\n")
            f.write(f"## System Overview\n\n{overview}\n\n")
            f.write(f"---\n\n")

            # Per-file timing summary
            if total_stats.get('timing'):
                f.write(f"## Timing Summary\n\n")
                file_stats = {}
                for fpath, fname, wall, tokens, llm, is_err in total_stats['timing']:
                    rel = os.path.relpath(fpath, directory)
                    if rel not in file_stats:
                        file_stats[rel] = {'wall': 0, 'llm': 0, 'tokens': 0, 'count': 0}
                    file_stats[rel]['wall'] += wall
                    file_stats[rel]['llm'] += llm
                    file_stats[rel]['tokens'] += tokens
                    file_stats[rel]['count'] += 1
                f.write(f"| File | Functions | Wall (s) | Tokens |\n")
                f.write(f"|------|-----------|----------|--------|\n")
                for fpath in sorted(file_stats.keys(), key=lambda x: -file_stats[x]['wall']):
                    s = file_stats[fpath]
                    f.write(f"| {fpath} | {s['count']} | {s['wall']:.1f} | {s['tokens']} |\n")
                f.write(f"\n---\n\n")

            f.write(f"## File Documentation\n\n")

            for filepath in sorted(all_results.keys()):
                results = all_results[filepath]
                rel_path = os.path.relpath(filepath, directory)
                max_line = max(r['end'] for r in results) if results else 0

                f.write(f"### {rel_path}\n\n")
                f.write(f"**Lines:** {max_line}\n\n")

                for r in results:
                    f.write(f"- Lines {r['start']}-{r['end']}: {r['type']} `{r['name']}` - {r['description']}\n")
                f.write(f"\n---\n\n")

        print(f"\nWritten to {output_file}")

    total_elapsed = time.time() - total_start
    total_stats['total_elapsed'] = total_elapsed
    print(f"\n=== COMPLETE: {total_elapsed:.1f}s total ===")

    return all_results, total_stats, overview


def main():
    parser = argparse.ArgumentParser(description='Document Python files by function')
    parser.add_argument('path', help='Python file or directory to document')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-f', '--force', action='store_true', help='Force reprocess all (ignore cache)')
    parser.add_argument('-w', '--workers', type=int, default=10, help='Number of concurrent LLM workers (default: 10)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed timing for each operation')
    parser.add_argument('--timing-log', help='Write detailed timing log to file')
    args = parser.parse_args()

    cache = load_cache()

    path = Path(args.path)

    if path.is_dir():
        # Directory mode - process all files and generate overview
        all_results, total_stats, overview = process_directory(
            str(path), cache, force=args.force, output_file=args.output, workers=args.workers,
            verbose=args.verbose, timing_log=args.timing_log
        )
        print(f"\n=== SUMMARY ===")
        print(f"Files: {len(all_results)}")
        print(f"Cache: {total_stats['cached']} cached, {total_stats['new']} new, {total_stats['changed']} changed")
    else:
        # Single file mode
        results, stats = process_file(str(path), cache, force=args.force)
        save_cache(cache)

        # Output
        print(f"\n=== RESULTS ({stats['cached']} cached, {stats['new']} new, {stats['changed']} changed) ===\n")
        print(f"{'Function':<30} {'Hash':<10} {'Status':<10} {'Lines':<12} Description")
        print("-" * 100)
        for r in results:
            name = r['name'][:28]
            desc = r['description'][:40] + "..." if len(r['description']) > 40 else r['description']
            print(f"{name:<30} {r['hash']:<10} {r['status']:<10} {r['start']}-{r['end']:<8} {desc}")

        if args.output:
            with open(args.output, 'w') as f:
                f.write(f"# Documentation: {args.path}\n\n")
                f.write(f"| Function | Lines | Hash | Description |\n")
                f.write(f"|----------|-------|------|-------------|\n")
                for r in results:
                    f.write(f"| `{r['name']}` | {r['start']}-{r['end']} | {r['hash']} | {r['description']} |\n")
            print(f"\nWritten to {args.output}")


if __name__ == '__main__':
    main()

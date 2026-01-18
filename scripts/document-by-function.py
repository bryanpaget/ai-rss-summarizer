"""Document Python files by extracting functions first, then describing each.

Uses AST for deterministic structure extraction, LLM only for descriptions.
Supports hash-based caching to skip unchanged functions.
"""
import sys
import ast
import os
import json
import hashlib
import argparse
from pathlib import Path

# Add src to path for gateway import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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
    with open(filepath) as f:
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
    """Call LLM via project's gateway (handles model loading)."""
    from gateway import get_gateway

    try:
        gateway = get_gateway()
        response = gateway.request_text(prompt)
        return response
    except Exception as e:
        return f"Error: {e}"


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
    """Get LLM to describe a single function using sandwich prompt structure."""
    code = func['code']
    tokens = estimate_tokens(code)

    # If too large, extract and describe nested functions separately
    if tokens > max_tokens and func['type'] in ('class', 'function'):
        nested = extract_nested_functions(code, func['name'])
        if nested:
            # Describe nested items individually
            nested_descs = []
            for nf in nested[:10]:  # Limit to avoid runaway
                nested_desc = describe_function(nf, max_tokens)
                nested_descs.append(f"  - {nf['name']}: {nested_desc}")

            # Summary for parent
            return f"Contains {len(nested)} methods: " + "; ".join([n['name'].split('.')[-1] for n in nested[:5]])

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

    response = call_llm(prompt)
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
    return desc


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
                desc = describe_function(func)
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


def process_directory(directory, cache, force=False, output_file=None):
    """Process all Python files in a directory."""
    py_files = find_python_files(directory)
    print(f"Found {len(py_files)} Python files in {directory}")

    all_results = {}
    total_stats = {'cached': 0, 'new': 0, 'changed': 0}

    for i, filepath in enumerate(py_files):
        print(f"\n[{i+1}/{len(py_files)}] Processing {os.path.relpath(filepath, directory)}...")
        try:
            results, stats = process_file(filepath, cache, force=force)
            all_results[filepath] = results
            total_stats['cached'] += stats['cached']
            total_stats['new'] += stats['new']
            total_stats['changed'] += stats['changed']
        except Exception as e:
            print(f"  ERROR: {e}")
            all_results[filepath] = []

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
            f.write(f"---\n\n")
            f.write(f"## System Overview\n\n{overview}\n\n")
            f.write(f"---\n\n")
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

    return all_results, total_stats, overview


def main():
    parser = argparse.ArgumentParser(description='Document Python files by function')
    parser.add_argument('path', help='Python file or directory to document')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-f', '--force', action='store_true', help='Force reprocess all (ignore cache)')
    args = parser.parse_args()

    cache = load_cache()

    path = Path(args.path)

    if path.is_dir():
        # Directory mode - process all files and generate overview
        all_results, total_stats, overview = process_directory(
            str(path), cache, force=args.force, output_file=args.output
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

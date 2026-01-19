"""Document codebases by extracting functions/classes from ALL file types.

Architecture:
1. Tree-sitter: Languages with grammars (Python, JS, TS, Go, Rust, Java, C, etc.)
2. LLM fallback: Text files without grammar support -> send to LLM for structure analysis
3. "Couldn't parse": Only if LLM returns unusable response

Uses hash-based caching to skip unchanged functions.
Uses concurrent processing to keep multiple LLM requests in flight.
"""
import sys
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
CACHE_FILE = CACHE_DIR / "codebase_docs.json"

# =============================================================================
# LANGUAGE CONFIGURATION
# =============================================================================

# Map file extensions to tree-sitter language names
EXTENSION_TO_LANGUAGE = {
    # Python
    '.py': 'python',
    '.pyw': 'python',
    '.pyi': 'python',

    # JavaScript/TypeScript
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.mjs': 'javascript',
    '.cjs': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',

    # Systems languages
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.hpp': 'cpp',
    '.hxx': 'cpp',
    '.rs': 'rust',
    '.go': 'go',

    # JVM languages
    '.java': 'java',

    # Scripting
    '.rb': 'ruby',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'bash',

    # Data/Config (parseable but may not have "functions")
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',

    # Web
    '.html': 'html',
    '.htm': 'html',
    '.css': 'css',
    '.sql': 'sql',

    # Docs
    '.md': 'markdown',
}

# Tree-sitter queries to extract code units per language
# Each query should capture 'name' for the identifier and optionally 'body'
LANGUAGE_QUERIES = {
    'python': """
        (function_definition name: (identifier) @name) @function
        (class_definition name: (identifier) @name) @class
    """,
    'javascript': """
        (function_declaration name: (identifier) @name) @function
        (class_declaration name: (identifier) @name) @class
        (method_definition name: (property_identifier) @name) @method
        (arrow_function) @arrow
        (variable_declarator name: (identifier) @name value: (arrow_function)) @arrow_var
        (variable_declarator name: (identifier) @name value: (function_expression)) @func_expr
    """,
    'typescript': """
        (function_declaration name: (identifier) @name) @function
        (class_declaration name: (identifier) @name) @class
        (method_definition name: (property_identifier) @name) @method
        (arrow_function) @arrow
        (variable_declarator name: (identifier) @name value: (arrow_function)) @arrow_var
        (interface_declaration name: (type_identifier) @name) @interface
        (type_alias_declaration name: (type_identifier) @name) @type_alias
    """,
    'go': """
        (function_declaration name: (identifier) @name) @function
        (method_declaration name: (field_identifier) @name) @method
        (type_declaration (type_spec name: (type_identifier) @name)) @type
    """,
    'rust': """
        (function_item name: (identifier) @name) @function
        (impl_item) @impl
        (struct_item name: (type_identifier) @name) @struct
        (enum_item name: (type_identifier) @name) @enum
        (trait_item name: (type_identifier) @name) @trait
    """,
    'java': """
        (method_declaration name: (identifier) @name) @method
        (class_declaration name: (identifier) @name) @class
        (interface_declaration name: (identifier) @name) @interface
        (constructor_declaration name: (identifier) @name) @constructor
    """,
    'c': """
        (function_definition declarator: (function_declarator declarator: (identifier) @name)) @function
        (struct_specifier name: (type_identifier) @name) @struct
        (enum_specifier name: (type_identifier) @name) @enum
    """,
    'cpp': """
        (function_definition declarator: (function_declarator declarator: (identifier) @name)) @function
        (function_definition declarator: (function_declarator declarator: (qualified_identifier) @name)) @function
        (class_specifier name: (type_identifier) @name) @class
        (struct_specifier name: (type_identifier) @name) @struct
    """,
    'ruby': """
        (method name: (identifier) @name) @method
        (class name: (constant) @name) @class
        (module name: (constant) @name) @module
    """,
    'bash': """
        (function_definition name: (word) @name) @function
    """,
}

# Languages where we don't extract functions (data/config files)
# We still parse them to validate syntax but just describe the file as a whole
DATA_LANGUAGES = {'json', 'yaml', 'toml', 'html', 'css', 'markdown', 'sql'}

# Text file extensions that get LLM analysis (no tree-sitter grammar)
TEXT_EXTENSIONS = {
    '.txt', '.rst', '.cfg', '.ini', '.conf', '.env', '.gitignore',
    '.dockerfile', '.makefile', '.cmake',
}


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

def load_cache():
    """Load cached function descriptions."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save function descriptions cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)


def hash_code(code: str) -> str:
    """Generate short hash of code for change detection."""
    return hashlib.md5(code.encode()).hexdigest()[:8]


# =============================================================================
# TREE-SITTER EXTRACTION
# =============================================================================

def get_language_for_file(filepath: str) -> str | None:
    """Get tree-sitter language name for a file, or None if not supported."""
    ext = Path(filepath).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext)


def extract_with_treesitter(filepath: str, language: str) -> list[dict]:
    """Extract code units using tree-sitter.

    Returns list of dicts with: name, type, start, end, code
    """
    from tree_sitter_language_pack import get_parser

    with open(filepath, encoding='utf-8', errors='replace') as f:
        content = f.read()

    lines = content.split('\n')
    parser = get_parser(language)
    tree = parser.parse(content.encode())

    results = []

    # For data languages, just describe the whole file
    if language in DATA_LANGUAGES:
        results.append({
            'name': Path(filepath).name,
            'type': f'{language}_file',
            'start': 1,
            'end': len(lines),
            'code': content[:2000] if len(content) > 2000 else content  # Limit for LLM
        })
        return results

    # Get query for this language
    query_text = LANGUAGE_QUERIES.get(language)
    if not query_text:
        # Language supported by tree-sitter but we don't have queries
        # Treat as text file
        return None

    try:
        from tree_sitter_language_pack import get_language
        lang = get_language(language)
        query = lang.query(query_text)
    except Exception as e:
        # Query failed - fall back to LLM
        print(f"    Query error for {language}: {e}")
        return None

    # Execute query and collect matches
    # API returns dict: {capture_name: [nodes]}
    captures_dict = query.captures(tree.root_node)

    # Get name nodes for lookup
    name_nodes = captures_dict.get('name', [])

    # Process all capture types except 'name' (which is just for identification)
    seen_ranges = set()
    for capture_name, nodes in captures_dict.items():
        if capture_name == 'name':
            continue

        for node in nodes:
            start_line = node.start_point[0] + 1  # 1-indexed
            end_line = node.end_point[0] + 1

            # Deduplicate (same range can match multiple patterns)
            range_key = (start_line, end_line)
            if range_key in seen_ranges:
                continue
            seen_ranges.add(range_key)

            code = node.text.decode('utf-8', errors='replace')

            # Try to find name from @name captures within this node's range
            name = None
            for name_node in name_nodes:
                if (name_node.start_point[0] >= node.start_point[0] and
                    name_node.end_point[0] <= node.end_point[0]):
                    name = name_node.text.decode('utf-8', errors='replace')
                    break

            if not name:
                # Fallback: use first line as identifier
                name = code.split('\n')[0][:50].strip()

            results.append({
                'name': name,
                'type': capture_name,
                'start': start_line,
                'end': end_line,
                'code': code
            })

    # Sort by start line
    results.sort(key=lambda x: x['start'])

    # If no results but file has content, add file-level entry
    if not results and content.strip():
        results.append({
            'name': Path(filepath).name,
            'type': 'file',
            'start': 1,
            'end': len(lines),
            'code': content[:2000] if len(content) > 2000 else content
        })

    return results


# =============================================================================
# PYTHON AST EXTRACTION (fallback for Python files if tree-sitter fails)
# =============================================================================

def extract_with_python_ast(filepath: str) -> list[dict]:
    """Use Python AST to extract all functions/classes with exact line numbers."""
    import ast

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


# =============================================================================
# LLM FUNCTIONS
# =============================================================================

class LLMError(Exception):
    """Raised when LLM call fails after all retries."""
    pass


# Global LLM backend configuration
_llm_backend = None  # 'gateway', 'lmstudio', or 'openai'
_llm_config = {}


def configure_llm(backend: str, **config):
    """Configure LLM backend.

    Backends:
    - 'gateway': Use project's gateway (requires gateway module in path)
    - 'lmstudio': Direct LM Studio API (config: base_url, model)
    - 'openai': OpenAI API (config: api_key, model)
    """
    global _llm_backend, _llm_config
    _llm_backend = backend
    _llm_config = config


def _detect_llm_backend():
    """Auto-detect available LLM backend."""
    global _llm_backend, _llm_config

    # Try gateway first (project-specific)
    try:
        from gateway import get_gateway
        _llm_backend = 'gateway'
        return
    except ImportError:
        pass

    # Try LM Studio (local)
    try:
        import httpx
        resp = httpx.get('http://localhost:1234/v1/models', timeout=2)
        if resp.status_code == 200:
            models = resp.json().get('data', [])
            if models:
                _llm_backend = 'lmstudio'
                _llm_config = {
                    'base_url': 'http://localhost:1234/v1',
                    'model': models[0]['id']
                }
                return
    except Exception:
        pass

    # Try OpenAI
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        _llm_backend = 'openai'
        _llm_config = {
            'api_key': api_key,
            'model': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        }
        return

    raise LLMError("No LLM backend available. Start LM Studio or set OPENAI_API_KEY.")


def _call_gateway(prompt: str) -> str:
    """Call LLM via project gateway."""
    from gateway import get_gateway
    gateway = get_gateway()
    return gateway.request_text(prompt)


def _call_lmstudio(prompt: str) -> str:
    """Call LM Studio directly."""
    import httpx
    response = httpx.post(
        f"{_llm_config['base_url']}/chat/completions",
        json={
            'model': _llm_config['model'],
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3,
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']


def _call_openai(prompt: str) -> str:
    """Call OpenAI API."""
    import httpx
    response = httpx.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f"Bearer {_llm_config['api_key']}"},
        json={
            'model': _llm_config['model'],
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3,
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']


def call_llm(prompt, max_retries=3, base_delay=2.0):
    """Call LLM with auto-detected or configured backend.

    Returns: (response, llm_time_seconds)
    Raises: LLMError if all retries fail
    """
    import time
    global _llm_backend

    if _llm_backend is None:
        _detect_llm_backend()
        print(f"  Using LLM backend: {_llm_backend}")

    # Select call function based on backend
    call_fn = {
        'gateway': _call_gateway,
        'lmstudio': _call_lmstudio,
        'openai': _call_openai,
    }.get(_llm_backend)

    if not call_fn:
        raise LLMError(f"Unknown LLM backend: {_llm_backend}")

    last_error = None
    total_time = 0

    for attempt in range(max_retries):
        t0 = time.time()
        try:
            response = call_fn(prompt)
            llm_time = time.time() - t0
            return response, llm_time
        except Exception as e:
            elapsed = time.time() - t0
            total_time += elapsed
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                print(f"    RETRY {attempt+1}/{max_retries}: {e} (waiting {delay}s)", flush=True)
                time.sleep(delay)

    # All retries failed - raise, don't return error string
    raise LLMError(f"Failed after {max_retries} attempts ({total_time:.1f}s total): {last_error}")


def estimate_tokens(text: str) -> int:
    """Estimate token count (roughly 4 chars per token)."""
    return len(text) // 4


def describe_code_unit(func: dict, language: str = 'unknown', max_tokens: int = 5000):
    """Get LLM to describe a single code unit.

    Returns: (description, timing_info)
        timing_info = {'llm_time': seconds, 'tokens_in': int}
    """
    code = func['code']
    tokens = estimate_tokens(code)
    timing_info = {'llm_time': 0.0, 'tokens_in': tokens}

    # Truncate code for prompt if too long
    code_for_prompt = code[:8000] if len(code) > 8000 else code

    # Determine type label for prompt
    type_label = func['type']
    if type_label in ('arrow', 'arrow_var', 'func_expr'):
        type_label = 'function'

    prompt = f"""You are a code documentation specialist creating concise summaries.

TASK: Write ONE sentence describing what this {language} {type_label} does.

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


def analyze_text_file_with_llm(filepath: str) -> list[dict]:
    """Use LLM to analyze a text file without grammar support.

    Returns list of extracted "units" or None if couldn't parse.
    """
    with open(filepath, encoding='utf-8', errors='replace') as f:
        content = f.read()

    if not content.strip():
        return []

    lines = content.split('\n')

    # For small files, just describe the whole thing
    if len(lines) < 50:
        return [{
            'name': Path(filepath).name,
            'type': 'file',
            'start': 1,
            'end': len(lines),
            'code': content
        }]

    # For larger files, ask LLM to identify sections
    prompt = f"""Analyze this file and identify its main sections or components.

FILE: {Path(filepath).name}
CONTENT (first 3000 chars):
{content[:3000]}

Return a JSON array of sections found, each with:
- "name": section identifier
- "type": what kind of section (config, target, rule, etc)
- "line": approximate starting line number

Example: [{{"name": "build", "type": "target", "line": 10}}, {{"name": "test", "type": "target", "line": 25}}]

Return ONLY the JSON array, no explanation:"""

    try:
        response, _ = call_llm(prompt)
        # Try to parse JSON from response
        response = response.strip()
        if response.startswith('```'):
            response = response.split('\n', 1)[1].rsplit('```', 1)[0]
        sections = json.loads(response)

        results = []
        for section in sections[:20]:  # Limit
            results.append({
                'name': section.get('name', 'unknown'),
                'type': section.get('type', 'section'),
                'start': section.get('line', 1),
                'end': section.get('line', 1) + 10,  # Approximate
                'code': ''  # Will be filled in later if needed
            })
        return results if results else [{
            'name': Path(filepath).name,
            'type': 'file',
            'start': 1,
            'end': len(lines),
            'code': content[:2000]
        }]
    except Exception:
        # LLM failed to parse - return file-level entry
        return [{
            'name': Path(filepath).name,
            'type': 'file',
            'start': 1,
            'end': len(lines),
            'code': content[:2000]
        }]


# =============================================================================
# MAIN EXTRACTION LOGIC
# =============================================================================

def extract_from_file(filepath: str) -> tuple[list[dict], str]:
    """Extract code units from any file type.

    Returns: (list of units, extraction_method)
    extraction_method is one of: 'treesitter', 'python_ast', 'llm', 'skipped'
    """
    ext = Path(filepath).suffix.lower()

    # Skip binary and generated files
    skip_extensions = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.dat',
                      '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
                      '.woff', '.woff2', '.ttf', '.eot',
                      '.zip', '.tar', '.gz', '.bz2', '.7z',
                      '.pdf', '.doc', '.docx', '.xls', '.xlsx'}
    if ext in skip_extensions:
        return [], 'skipped'

    # Try tree-sitter first
    language = get_language_for_file(filepath)
    if language:
        try:
            results = extract_with_treesitter(filepath, language)
            if results is not None:
                return results, 'treesitter'
        except Exception as e:
            print(f"    Tree-sitter failed for {filepath}: {e}")

    # For Python, fall back to AST
    if ext == '.py':
        try:
            results = extract_with_python_ast(filepath)
            return results, 'python_ast'
        except Exception as e:
            print(f"    Python AST failed for {filepath}: {e}")

    # For text-like files, use LLM
    if ext in TEXT_EXTENSIONS or (not language and is_text_file(filepath)):
        try:
            results = analyze_text_file_with_llm(filepath)
            return results, 'llm'
        except Exception as e:
            print(f"    LLM analysis failed for {filepath}: {e}")

    # Last resort: couldn't parse
    return [], 'skipped'


def is_text_file(filepath: str, sample_size: int = 8192) -> bool:
    """Check if a file appears to be text (not binary)."""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(sample_size)
        # Check for null bytes (binary indicator)
        if b'\x00' in chunk:
            return False
        # Try to decode as UTF-8
        try:
            chunk.decode('utf-8')
            return True
        except UnicodeDecodeError:
            return False
    except Exception:
        return False


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def find_files(directory: str, exclude_patterns: list[str] = None) -> list[str]:
    """Recursively find all processable files in directory."""
    exclude_patterns = exclude_patterns or [
        '.venv', 'venv', '__pycache__', '.git', 'build', 'dist',
        'node_modules', 'target', '.tox', 'htmlcov', 'archive',
        '.auto-claude', '.cache', '.pytest_cache', '.mypy_cache'
    ]

    files = []
    for root, dirs, filenames in os.walk(directory):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_patterns]

        for f in filenames:
            filepath = os.path.join(root, f)
            ext = Path(f).suffix.lower()

            # Include files with known extensions or that look like text
            if ext in EXTENSION_TO_LANGUAGE or ext in TEXT_EXTENSIONS:
                files.append(filepath)
            elif not ext and is_text_file(filepath):
                # No extension but is text (Makefile, Dockerfile, etc.)
                files.append(filepath)

    return sorted(files)


# =============================================================================
# PROCESSING
# =============================================================================

def process_directory(directory, cache, force=False, output_file=None, workers=10,
                     verbose=False, timing_log=None):
    """Process all files in a directory with concurrent LLM calls."""
    import time
    total_start = time.time()

    files = find_files(directory)
    print(f"Found {len(files)} files in {directory}")

    # Phase 1: Extract all code units from all files (mostly fast, tree-sitter)
    print("\n=== Phase 1: Extracting code structure ===")
    all_extractions = {}  # filepath -> (list of units, method)
    method_counts = {'treesitter': 0, 'python_ast': 0, 'llm': 0, 'skipped': 0}

    for i, filepath in enumerate(files):
        rel_path = os.path.relpath(filepath, directory)
        try:
            units, method = extract_from_file(filepath)
            all_extractions[filepath] = units
            method_counts[method] += 1
            if verbose or method == 'llm':
                print(f"  [{i+1}/{len(files)}] {rel_path}: {len(units)} units ({method})")
            else:
                print(f"  [{i+1}/{len(files)}] {rel_path}: {len(units)} units")
        except Exception as e:
            print(f"  [{i+1}/{len(files)}] {rel_path}: ERROR - {e}")
            all_extractions[filepath] = []
            method_counts['skipped'] += 1

    print(f"\nExtraction methods: {method_counts}")

    # Phase 2: Build work queue (items needing LLM descriptions)
    print("\n=== Phase 2: Building work queue ===")
    work_queue = []
    total_stats = {'cached': 0, 'new': 0, 'changed': 0}

    for filepath, units in all_extractions.items():
        file_cache = cache.get(str(Path(filepath).resolve()), {})
        language = get_language_for_file(filepath) or 'unknown'

        for unit in units:
            code_hash = hash_code(unit['code'])
            cached_entry = file_cache.get(unit['name'], {})
            cached_hash = cached_entry.get('hash', '')
            cached_desc = cached_entry.get('description', '')

            # Skip certain types that don't need LLM
            if unit['type'] == 'import-block':
                unit['_description'] = "Module imports"
                unit['_status'] = 'skip'
                total_stats['cached'] += 1
            elif unit['type'] == 'global' and unit['name'] == 'module_docstring':
                unit['_description'] = "Module docstring"
                unit['_status'] = 'skip'
                total_stats['cached'] += 1
            elif not force and cached_hash == code_hash and cached_desc:
                unit['_description'] = cached_desc
                unit['_status'] = 'cached'
                total_stats['cached'] += 1
            else:
                status = 'FORCED' if force else ('CHANGED' if cached_hash else 'NEW')
                unit['_status'] = status
                unit['_hash'] = code_hash
                unit['_language'] = language
                work_queue.append((filepath, unit))
                if status == 'NEW':
                    total_stats['new'] += 1
                elif status == 'CHANGED':
                    total_stats['changed'] += 1

    print(f"  {len(work_queue)} items need LLM, {total_stats['cached']} cached")

    # Phase 3: Concurrent LLM processing
    if work_queue:
        total = len(work_queue)
        completed = 0
        queue_size = workers
        work_iter = iter(work_queue)
        pending = {}
        timing_data = []
        phase3_start = time.time()

        print(f"\n=== Phase 3: LLM descriptions (queue={queue_size}, total={total}) ===", flush=True)

        def process_item(item):
            import time as t
            t0 = t.time()
            filepath, unit = item
            language = unit.get('_language', 'unknown')
            desc, timing_info = describe_code_unit(unit, language)
            timing_info['total_time'] = t.time() - t0
            return filepath, unit, desc, timing_info

        with ThreadPoolExecutor(max_workers=queue_size) as executor:
            # Fill queue
            for _ in range(min(queue_size, total)):
                try:
                    item = next(work_iter)
                    future = executor.submit(process_item, item)
                    pending[future] = (item[0], item[1], time.time())
                except StopIteration:
                    break

            total_tokens = 0
            total_llm_time = 0.0
            fatal_error = None

            while pending and not fatal_error:
                done = next(as_completed(pending.keys()))
                filepath_orig, unit_orig, start_time = pending.pop(done)

                try:
                    filepath, unit, desc, timing_info = done.result()
                except LLMError as e:
                    fatal_error = f"{os.path.relpath(filepath_orig, directory)}:{unit_orig['name']}: {e}"
                    print(f"\n\n  FATAL ERROR: {fatal_error}", flush=True)
                    for f in pending:
                        f.cancel()
                    break
                except Exception as e:
                    fatal_error = f"{os.path.relpath(filepath_orig, directory)}:{unit_orig['name']}: {e}"
                    print(f"\n\n  FATAL ERROR: {fatal_error}", flush=True)
                    for f in pending:
                        f.cancel()
                    break

                wall_time = time.time() - start_time
                tokens = timing_info['tokens_in']
                llm_time = timing_info['llm_time']
                total_tokens += tokens
                total_llm_time += llm_time
                unit['_description'] = desc
                completed += 1
                timing_data.append((filepath, unit['name'], wall_time, tokens, llm_time))

                if verbose:
                    print(f"  [{completed}/{total}] {os.path.relpath(filepath, directory)}:{unit['name']}", flush=True)
                else:
                    print(f"\r  Processing: {completed}/{total} ({total_tokens} tokens)", end='', flush=True)

                # Replenish queue
                try:
                    item = next(work_iter)
                    future = executor.submit(process_item, item)
                    pending[future] = (item[0], item[1], time.time())
                except StopIteration:
                    pass

            if fatal_error:
                raise LLMError(f"Documentation run aborted: {fatal_error}")

        phase3_duration = time.time() - phase3_start
        if not verbose:
            print()
        print(f"\n  Phase 3 complete: {phase3_duration:.1f}s, {total_tokens} tokens")
        total_stats['timing'] = timing_data
        total_stats['phase3_duration'] = phase3_duration

    # Phase 4: Assemble results and update cache
    print("\n=== Phase 4: Assembling results ===")
    all_results = {}

    for filepath, units in all_extractions.items():
        filepath_resolved = str(Path(filepath).resolve())
        file_cache = cache.get(filepath_resolved, {})
        results = []

        for unit in units:
            code_hash = unit.get('_hash', hash_code(unit['code']))
            desc = unit.get('_description', '')
            status = unit.get('_status', 'unknown')

            file_cache[unit['name']] = {
                'hash': code_hash,
                'description': desc,
                'start': unit['start'],
                'end': unit['end'],
                'type': unit['type']
            }

            results.append({
                'start': unit['start'],
                'end': unit['end'],
                'type': unit['type'],
                'name': unit['name'],
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
        write_output(output_file, all_results, directory, total_stats, project_stats, overview)
        print(f"\nWritten to {output_file}")

    total_elapsed = time.time() - total_start
    print(f"\n=== COMPLETE: {total_elapsed:.1f}s total ===")

    return all_results, total_stats, overview


def generate_overview(all_results, directory):
    """Generate system architecture overview from all file documentation."""
    files_data = []
    total_functions = 0
    total_classes = 0
    total_lines = 0

    for filepath, results in all_results.items():
        if not results:
            continue
        rel_path = os.path.relpath(filepath, directory)
        functions = [r for r in results if r['type'] in ('function', 'method', 'arrow', 'arrow_var', 'func_expr')]
        classes = [r for r in results if r['type'] in ('class', 'struct', 'interface', 'type', 'enum', 'trait')]
        max_line = max((r['end'] for r in results), default=0)

        files_data.append({
            'path': rel_path,
            'functions': functions,
            'classes': classes,
            'line_count': max_line
        })

        total_functions += len(functions)
        total_classes += len(classes)
        total_lines += max_line

    # Build overview prompt
    file_summaries = []
    for fd in files_data[:30]:  # Limit for prompt size
        func_names = [f['name'] for f in fd['functions'][:5]]
        class_names = [c['name'] for c in fd['classes'][:5]]
        summary = f"- **{fd['path']}** ({fd['line_count']} lines): "
        if class_names:
            summary += f"Classes: {', '.join(class_names)}. "
        if func_names:
            summary += f"Functions: {', '.join(func_names)}"
        file_summaries.append(summary)

    overview_prompt = f"""You are a software architect creating a system overview document.

TASK: Create a concise architecture overview for this codebase.

PROJECT STATS:
- {len(files_data)} files
- {total_functions} functions/methods
- {total_classes} classes/types
- ~{total_lines} total lines

FILE SUMMARIES:
{chr(10).join(file_summaries)}

Create a brief architecture overview with these sections:
1. **Purpose**: What does this project do? (1-2 sentences)
2. **Key Modules**: List 3-5 most important files and their roles
3. **Entry Points**: Where does execution start?
4. **Languages/Stack**: What technologies are used?

Keep it under 300 words. Be specific to THIS codebase."""

    overview, _ = call_llm(overview_prompt)
    return overview, {
        'files': len(files_data),
        'functions': total_functions,
        'classes': total_classes,
        'lines': total_lines
    }


def write_output(output_file, all_results, directory, total_stats, project_stats, overview):
    """Write documentation to output file."""
    from datetime import datetime

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Project Documentation\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Stats:** {project_stats['files']} files, {project_stats['functions']} functions, ")
        f.write(f"{project_stats['classes']} classes, ~{project_stats['lines']} lines\n\n")
        f.write(f"**Cache:** {total_stats['cached']} cached, {total_stats['new']} new, {total_stats['changed']} changed\n\n")

        if 'phase3_duration' in total_stats:
            f.write(f"**Timing:** {total_stats['phase3_duration']:.1f}s LLM time\n\n")

        f.write(f"---\n\n")
        f.write(f"## System Overview\n\n{overview}\n\n")
        f.write(f"---\n\n")
        f.write(f"## File Documentation\n\n")

        for filepath in sorted(all_results.keys()):
            results = all_results[filepath]
            if not results:
                continue
            rel_path = os.path.relpath(filepath, directory)
            max_line = max((r['end'] for r in results), default=0)

            f.write(f"### {rel_path}\n\n")
            f.write(f"**Lines:** {max_line}\n\n")

            for r in results:
                f.write(f"- Lines {r['start']}-{r['end']}: {r['type']} `{r['name']}` - {r['description']}\n")
            f.write(f"\n---\n\n")


def main():
    parser = argparse.ArgumentParser(
        description='Document codebases by extracting functions/classes from ALL file types'
    )
    parser.add_argument('path', help='Directory to document')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-f', '--force', action='store_true', help='Force reprocess all (ignore cache)')
    parser.add_argument('-w', '--workers', type=int, default=10, help='Number of concurrent LLM workers')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed progress')
    parser.add_argument('--timing-log', help='Write detailed timing log to file')
    args = parser.parse_args()

    cache = load_cache()
    path = Path(args.path)

    if not path.is_dir():
        print(f"Error: {args.path} is not a directory")
        sys.exit(1)

    all_results, total_stats, overview = process_directory(
        str(path), cache,
        force=args.force,
        output_file=args.output,
        workers=args.workers,
        verbose=args.verbose,
        timing_log=args.timing_log
    )

    print(f"\n=== SUMMARY ===")
    print(f"Files: {len(all_results)}")
    print(f"Cache: {total_stats['cached']} cached, {total_stats['new']} new, {total_stats['changed']} changed")


if __name__ == '__main__':
    main()

"""Document Python files by extracting functions first, then describing each."""
import sys
import ast
import subprocess
import tempfile
import os
import json
from pathlib import Path

def extract_functions(filepath):
    """Use AST to extract all functions/classes with exact line numbers."""
    with open(filepath) as f:
        content = f.read()
    
    tree = ast.parse(content)
    lines = content.split('\n')
    
    results = []
    
    # Get module docstring if present
    if (ast.get_docstring(tree)):
        results.append({
            'name': 'module_docstring',
            'type': 'global',
            'start': 1,
            'end': 1,
            'code': ast.get_docstring(tree)
        })
    
    # Get top-level imports
    import_lines = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_lines.append(node.lineno)
    
    if import_lines:
        results.append({
            'name': 'imports',
            'type': 'import-block',
            'start': min(import_lines),
            'end': max(import_lines),
            'code': 'Import statements'
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
                    results.append({
                        'name': target.id,
                        'type': 'constant',
                        'start': node.lineno,
                        'end': node.end_lineno,
                        'code': lines[node.lineno-1]
                    })
    
    results.sort(key=lambda x: x['start'])
    return results

def call_llm(prompt):
    """Call LLM via gateway."""
    # Use project's gateway script (required for portability per CLAUDE.md)
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "safe-model-load.sh")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(prompt)
        prompt_file = f.name
    
    try:
        # Convert path for bash and escape spaces
        unix_prompt = prompt_file.replace('\\', '/').replace('C:', '/c').replace(' ', '\\ ')
        unix_script = script_path.replace('\\', '/').replace('C:', '/c').replace(' ', '\\ ')

        # Use bash -c with escaped paths
        cmd = f'{unix_script} request text --prompt-file {unix_prompt}'
        result = subprocess.run(
            ['bash', '-c', cmd],
            capture_output=True, text=True, timeout=120
        )
        
        # Parse FILE= from output
        for line in result.stdout.split('\n'):
            if line.startswith('FILE='):
                response_file = line[5:]
                # Convert back to Windows path if needed
                if response_file.startswith('/c/'):
                    response_file = 'C:' + response_file[2:]
                response_file = response_file.replace('/', '\\')
                
                # Wait for response
                import time
                for _ in range(60):
                    if os.path.exists(response_file) and os.path.getsize(response_file) > 0:
                        with open(response_file) as rf:
                            content = rf.read()
                            try:
                                data = json.loads(content)
                                if 'choices' in data:
                                    return data['choices'][0]['message']['content']
                            except:
                                return content
                    time.sleep(1)
        
        return f"Error: {result.stderr}"
    finally:
        os.unlink(prompt_file)

def describe_function(func):
    """Get LLM to describe a single function."""
    prompt = f"""Describe this Python {func['type']} in ONE sentence. Be specific about what it does.

{func['code'][:2000]}

ONE SENTENCE DESCRIPTION:"""
    
    response = call_llm(prompt)
    # Take first sentence only
    desc = response.strip().split('\n')[0].strip()
    if desc.startswith('This '):
        desc = desc[5:]
    return desc

def main():
    filepath = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Extracting functions from {filepath}...")
    functions = extract_functions(filepath)
    print(f"Found {len(functions)} items")
    
    results = []
    for i, func in enumerate(functions):
        print(f"  [{i+1}/{len(functions)}] {func['type']}: {func['name']}...", end='', flush=True)
        
        if func['type'] == 'import-block':
            desc = "Module imports"
        elif func['type'] == 'global' and func['name'] == 'module_docstring':
            desc = "Module docstring"
        else:
            desc = describe_function(func)
        
        results.append({
            'start': func['start'],
            'end': func['end'],
            'type': func['type'],
            'name': func['name'],
            'description': desc
        })
        print(f" done")
    
    # Output
    print("\n=== RESULTS ===\n")
    for r in results:
        line = f"Lines {r['start']}-{r['end']}: {r['type']} `{r['name']}` - {r['description']}"
        print(line)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(f"# Documentation: {filepath}\n\n")
            for r in results:
                f.write(f"- Lines {r['start']}-{r['end']}: {r['type']} `{r['name']}` - {r['description']}\n")
        print(f"\nWritten to {output_file}")

if __name__ == '__main__':
    main()

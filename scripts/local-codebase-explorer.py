#!/usr/bin/env python3
"""
Stub script for local-codebase-explorer.

This is a thin wrapper that imports from the local-codebase-explorer package.
Install the package with: pip install git+https://github.com/KatsuJinCode/local-codebase-explorer

Canonical source: https://github.com/KatsuJinCode/local-codebase-explorer
"""

if __name__ == "__main__":
    try:
        from local_codebase_explorer.explorer import main
        main()
    except ImportError as e:
        print("Error: local-codebase-explorer package not installed.")
        print("Install with: pip install git+https://github.com/KatsuJinCode/local-codebase-explorer")
        raise SystemExit(1) from e

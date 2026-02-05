#!/bin/bash
# Auto-installer for RSS Summarizer (Mac/Linux)
# This script installs pipx if needed, then installs the RSS summarizer

echo ""
echo "=== RSS Summarizer Installer ==="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python from https://python.org and try again."
    exit 1
fi

# Check if pipx is available
if ! command -v pipx &> /dev/null; then
    echo "pipx not found. Installing pipx..."
    python3 -m pip install --user pipx

    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install pipx."
        exit 1
    fi

    echo ""
    echo "Adding pipx to PATH..."
    python3 -m pipx ensurepath

    echo ""
    echo "====================================================="
    echo "IMPORTANT: Please restart your terminal, then run"
    echo "this installer again to complete the installation."
    echo "====================================================="
    exit 0
fi

echo "pipx found. Installing RSS Summarizer..."
echo ""

# Get the directory where this script lives
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install from current directory if pyproject.toml exists, otherwise from PyPI
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    echo "Installing from local source..."
    pipx install "$SCRIPT_DIR"
else
    echo "Installing from PyPI..."
    pipx install rss-summarizer
fi

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Installation failed."
    echo "If you see 'already installed', run: pipx reinstall rss-summarizer"
    exit 1
fi

echo ""
echo "====================================================="
echo "SUCCESS! RSS Summarizer is now installed."
echo ""
echo "You can now use these commands from anywhere:"
echo "  rss --help      Show all commands"
echo "  rss setup       Configure your LLM provider"
echo "  rss update      Fetch and summarize new articles"
echo ""
echo "If 'rss' is not recognized, restart your terminal first."
echo "====================================================="

#!/bin/bash
# install.sh - MyWtfUI Framework Installer
# Usage: curl -LsSf https://wtfui.dev/install.sh | bash

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}Installing MyWtfUI Framework...${NC}"
echo ""

# Check Python 3.14+
echo "Checking Python version..."
if command -v python3.14 &> /dev/null; then
    PYTHON_CMD="python3.14"
elif command -v python3 &> /dev/null; then
    # Use Python itself for reliable version comparison
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 14) else 1)"; then
        PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        echo -e "${RED}Error: Python 3.14+ required (found ${PY_VERSION})${NC}"
        echo "WtfUI requires Python 3.14+ for No-GIL support."
        echo ""
        echo "Install Python 3.14:"
        echo "  macOS:  brew install python@3.14"
        echo "  Ubuntu: add-apt-repository ppa:deadsnakes/ppa && apt install python3.14"
        echo "  Or:     https://www.python.org/downloads/"
        exit 1
    fi
    PYTHON_CMD="python3"
else
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}Found Python: $("${PYTHON_CMD}" --version)${NC}"

# Install uv if not present
echo ""
echo "Checking for uv package manager..."
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    if ! curl -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh; then
        echo -e "${RED}Error: Failed to download uv installer${NC}"
        exit 1
    fi
    sh /tmp/uv-install.sh
    rm -f /tmp/uv-install.sh

    # Add to PATH for current session
    export PATH="${HOME}/.cargo/bin:${PATH}"

    if ! command -v uv &> /dev/null; then
        echo -e "${RED}Error: uv installation failed${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}Found uv: $(uv --version)${NC}"

# Install WtfUI globally
echo ""
echo "Installing WtfUI..."
if ! uv tool install wtfui; then
    echo -e "${RED}Error: Failed to install WtfUI${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}${BOLD}WtfUI installed successfully!${NC}"
echo ""
echo "Get started:"
echo "  wtfui init myapp     Create a new project"
echo "  wtfui dev myapp      Start development server"
echo ""
echo "Documentation: https://wtfui.dev/docs"

#!/bin/bash
# CHATTA Quick Installer
# One-command installation: curl -fsSL https://chatta.ai/install | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}"
echo " ██████╗██╗  ██╗ █████╗ ████████╗████████╗ █████╗ "
echo "██╔════╝██║  ██║██╔══██╗╚══██╔══╝╚══██╔══╝██╔══██╗"
echo "██║     ███████║███████║   ██║      ██║   ███████║"
echo "██║     ██╔══██║██╔══██║   ██║      ██║   ██╔══██║"
echo "╚██████╗██║  ██║██║  ██║   ██║      ██║   ██║  ██║"
echo " ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝"
echo ""
echo "Natural Voice Conversations for AI Assistants • Part of the BUMBA Platform"
echo -e "${NC}\n"

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    CYGWIN*|MINGW*|MSYS*) MACHINE=Windows;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo -e "${BOLD}Detected OS:${NC} ${MACHINE}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "🔴 ${RED}Python 3 is not installed${NC}"
    echo "Please install Python 3.10+ first:"
    echo "  • macOS: brew install python3"
    echo "  • Linux: sudo apt install python3"
    echo "  • Windows: https://python.org/downloads"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "🟢 ${GREEN}Python ${PYTHON_VERSION} detected${NC}"

# Install CHATTA
echo -e "\n${BOLD}Installing CHATTA...${NC}"

# Check if pip is available
if ! python3 -m pip --version &> /dev/null; then
    echo "Installing pip..."
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | python3
fi

# Install or upgrade CHATTA
python3 -m pip install --upgrade chatta

# Download and run the setup wizard
echo -e "\n${BOLD}Starting interactive setup...${NC}\n"

# Create temporary directory for setup
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Download setup wizard
curl -fsSL https://raw.githubusercontent.com/your-repo/chatta/main/setup_wizard.py -o setup_wizard.py

# Run the wizard
python3 setup_wizard.py

# Cleanup
cd - > /dev/null
rm -rf "$TEMP_DIR"

echo -e "\n🏁 ${GREEN}${BOLD}Installation complete!${NC}"
echo -e "Run ${BLUE}chatta${NC} to start using CHATTA with Claude Code"

#!/bin/bash
# Test script to verify install.sh changes

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Testing VoiceMode install.sh modifications..."
echo

# 1. Check UV tool install command
echo "1. Checking UV tool install command..."
if grep -q "uv tool install --upgrade voice-mode" install.sh; then
    echo -e "${GREEN}✅ UV tool install uses --upgrade flag${NC}"
else
    echo -e "${RED}❌ UV tool install not using --upgrade flag${NC}"
fi

# 2. Check UV tool update-shell command
echo "2. Checking UV tool update-shell command..."
if grep -q "uv tool update-shell" install.sh; then
    echo -e "${GREEN}✅ UV tool update-shell is called${NC}"
else
    echo -e "${RED}❌ UV tool update-shell is not called${NC}"
fi

# 3. Check MCP configuration doesn't use uvx --refresh
echo "3. Checking MCP configuration..."
if grep -q "uvx --refresh" install.sh; then
    echo -e "${RED}❌ Still using uvx --refresh in MCP configuration${NC}"
    grep -n "uvx --refresh" install.sh
else
    echo -e "${GREEN}✅ No uvx --refresh in MCP configuration${NC}"
fi

# 4. Check fish shell support is removed
echo "4. Checking fish shell support..."
fish_count=$(grep -c "fish" install.sh | true)
if [[ $fish_count -eq 0 ]]; then
    echo -e "${GREEN}✅ Fish shell support completely removed${NC}"
else
    echo -e "${YELLOW}⚠️  Found $fish_count references to 'fish' - verify if intended${NC}"
fi

# 5. Check for Homebrew zsh completion support
echo "5. Checking Homebrew zsh completion support..."
if grep -q "brew --prefix" install.sh && grep -q "share/zsh/site-functions" install.sh; then
    echo -e "${GREEN}✅ Homebrew zsh completion support detected${NC}"
else
    echo -e "${RED}❌ Homebrew zsh completion support not found${NC}"
fi

# 6. Check for XDG-compliant bash completion
echo "6. Checking XDG-compliant bash completion..."
if grep -q 'XDG_DATA_HOME:-$HOME/.local/share' install.sh; then
    echo -e "${GREEN}✅ XDG-compliant bash completion path used${NC}"
else
    echo -e "${RED}❌ XDG-compliant bash completion path not found${NC}"
fi

# 7. Check zsh completion file naming
echo "7. Checking zsh completion file naming..."
if grep -q "_voicemode" install.sh; then
    echo -e "${GREEN}✅ Zsh completion uses underscore prefix (_voicemode)${NC}"
else
    echo -e "${RED}❌ Zsh completion not using underscore prefix${NC}"
fi

echo
echo "Test complete!"
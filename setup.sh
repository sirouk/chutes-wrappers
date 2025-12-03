#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Chutes Wrappers Setup Script
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Chutes Wrappers Setup${NC}"
echo ""

# Create virtual environment
if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Activate
source "$VENV_DIR/bin/activate"

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Activate the environment:"
echo -e "     ${YELLOW}source .venv/bin/activate${NC}"
echo ""
echo "  2. Register with Chutes (if not already):"
echo -e "     ${YELLOW}chutes register${NC}"
echo ""
echo "  3. Create your first chute:"
echo -e "     ${YELLOW}cp deploy_example.py deploy_myservice.py${NC}"
echo -e "     ${YELLOW}# Edit deploy_myservice.py${NC}"
echo ""
echo "  4. Build and deploy:"
echo -e "     ${YELLOW}./deploy.sh${NC}"


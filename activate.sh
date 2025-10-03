#!/bin/bash
# Activation script for DynamoDB Table Cloner

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 DynamoDB Table Cloner${NC}"
echo "=========================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found."
    echo "Run: make venv"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}✅ Activating virtual environment...${NC}"
source .venv/bin/activate

# Show status
echo -e "${GREEN}✅ Virtual environment activated!${NC}"
echo ""
echo "Available commands:"
echo "  python table_cloner.py <table_name>  - Clone a table"
echo "  python test_setup.py                 - Verify setup"
echo "  python example_usage.py              - Run batch cloning example"
echo "  make clone TABLE=<table_name>        - Clone using make"
echo ""
echo "Example:"
echo "  python table_cloner.py dev_users"
echo ""
echo "To deactivate: deactivate"
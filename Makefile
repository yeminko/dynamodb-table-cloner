.PHONY: help install install-uv venv test setup clone example clean

# Default target
help:
	@echo "DynamoDB Table Cloner - Available Commands:"
	@echo ""
	@echo "  make install      - Install Python dependencies (auto-detect uv/pip)"
	@echo "  make install-uv   - Install dependencies using uv"
	@echo "  make venv         - Create virtual environment with uv and install deps"
	@echo "  make test         - Run setup verification tests"
	@echo "  make setup        - Install dependencies and run tests"
	@echo "  make clone        - Clone a specific table (TABLE=table_name)"
	@echo "  make example      - Run example batch cloning"
	@echo "  make clean        - Clean up Python cache files"
	@echo ""
	@echo "Examples:"
	@echo "  make clone TABLE=dev_users"
	@echo "  make venv         # Create virtual environment"
	@echo "  make setup"

# Install dependencies (auto-detect uv/pip)
install:
	@echo "📦 Installing Python dependencies..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "Using uv..."; \
		if [ -n "$$VIRTUAL_ENV" ] || [ -d ".venv" ]; then \
			uv pip install -r requirements.txt; \
		else \
			echo "No virtual environment detected. Installing system-wide..."; \
			uv pip install --system -r requirements.txt; \
		fi; \
	elif command -v pip >/dev/null 2>&1; then \
		echo "Using pip..."; \
		pip install -r requirements.txt; \
	else \
		echo "❌ Error: Neither uv nor pip found. Please install one of them."; \
		exit 1; \
	fi

# Install dependencies using uv specifically
install-uv:
	@echo "📦 Installing Python dependencies with uv..."
	@if command -v uv >/dev/null 2>&1; then \
		if [ -n "$$VIRTUAL_ENV" ] || [ -d ".venv" ]; then \
			uv pip install -r requirements.txt; \
		else \
			echo "No virtual environment detected. Installing system-wide..."; \
			uv pip install --system -r requirements.txt; \
		fi; \
	else \
		echo "❌ Error: uv not found. Please install uv first."; \
		echo "Visit: https://docs.astral.sh/uv/getting-started/installation/"; \
		exit 1; \
	fi

# Create virtual environment and install dependencies
venv:
	@echo "🐍 Creating virtual environment with uv..."
	@if command -v uv >/dev/null 2>&1; then \
		uv venv; \
		echo "Virtual environment created in .venv/"; \
		echo "To activate: source .venv/bin/activate"; \
		echo "Installing dependencies..."; \
		uv pip install -r requirements.txt; \
	else \
		echo "❌ Error: uv not found. Please install uv first."; \
		exit 1; \
	fi

# Run setup verification
test:
	@echo "🔍 Running setup verification..."
	python test_setup.py

# Setup project (install + test)
setup: install test
	@echo "✅ Project setup completed!"

# Clone a specific table
clone:
	@if [ -z "$(TABLE)" ]; then \
		echo "❌ Error: Please specify a table name using TABLE=table_name"; \
		echo "Example: make clone TABLE=dev_users"; \
		exit 1; \
	fi
	@echo "🚀 Cloning table: $(TABLE)"
	python table_cloner.py $(TABLE)

# Run example batch cloning
example:
	@echo "🚀 Running example batch cloning..."
	python example_usage.py

# Clean up Python cache files
clean:
	@echo "🧹 Cleaning up Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed!"
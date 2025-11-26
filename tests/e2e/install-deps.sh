#!/bin/bash
# Install dependencies for E2E test suite

echo "🔧 Installing E2E test dependencies..."
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install pytest and plugins
echo ""
echo "📦 Installing pytest and plugins..."
pip3 install pytest pytest-cov pytest-xdist pytest-timeout

echo ""
echo "✅ Installation complete!"
echo ""
echo "Run tests with:"
echo "  cd tests/e2e"
echo "  pytest -v"

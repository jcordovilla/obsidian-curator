#!/bin/bash
# Simple script to run tests with Poetry

echo "🧪 Obsidian Note Curator - Test Runner"
echo "======================================"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Please install it first:"
    echo "curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check if dependencies are installed
if [ ! -f "poetry.lock" ]; then
    echo "📦 Installing dependencies..."
    poetry install
fi

echo ""
echo "Choose an option:"
echo "1. Test the system (100 random notes)"
echo "2. Process entire vault (all notes)"
echo "3. Review results"
echo "4. Run all tests"
echo ""

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "🧪 Running system test..."
        poetry run python test_classification_system.py
        ;;
    2)
        echo "📚 Processing entire vault..."
        poetry run python process_vault.py
        ;;
    3)
        echo "🔍 Reviewing results..."
        poetry run python review_classification_results.py
        ;;
    4)
        echo "🔄 Running all tests..."
        echo "1. Testing system..."
        poetry run python test_classification_system.py
        echo ""
        echo "2. Processing vault..."
        poetry run python process_vault.py
        echo ""
        echo "3. Reviewing results..."
        poetry run python review_classification_results.py
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac 
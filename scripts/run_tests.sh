#!/bin/bash

# Script for running tests for coordinates-lit project

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Virtual environment is not active. Please activate the environment."
    exit 1
fi

# Run tests with code coverage
echo "Running tests with code coverage..."
pytest --cov=src --cov-report=term-missing tests/

# Type checking
echo "Checking types..."
mypy src/

# Code formatting
echo "Formatting code..."
black src/ tests/
isort src/ tests/

echo "Tests completed!"
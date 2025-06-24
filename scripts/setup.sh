#!/bin/bash

# Installation script for coordinates-lit project

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip is not installed. Please install pip."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -e .

# Install development dependencies
echo "Installing development dependencies..."
pip install -e ".[dev]"

# Create data directories
echo "Creating data directories..."
mkdir -p data/{raw,processed,cache}

# Create configuration files
echo "Creating configuration files..."
cp config/development.yaml config/local.yaml

echo "Installation completed successfully!"
echo "To activate the environment, use: source venv/bin/activate"
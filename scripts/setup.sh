#!/bin/bash

set -e  # Exit on error

# Install Python 3.11 if not installed
if ! command -v python3.11 &> /dev/null; then
    echo "Installing Python 3.11..."
    brew install python@3.11
fi

# Ensure pip3.11 is used
echo "Installing dependencies with pip3.11..."
python3.11 -m pip install --upgrade pip
python3.11 -m pip install -r requirements.txt

python3.11 -m pip install .

echo "✅ Setup complete. You can now run Stressandra!"

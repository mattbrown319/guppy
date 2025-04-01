#!/bin/bash

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

echo "Virtual environment is set up and activated."
echo "To use it in the future, run: source venv/bin/activate"
echo "Then run: python jira_client.py" 
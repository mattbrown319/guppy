#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Virtual environment activated"
fi

# First test the JIRA connection
echo "Testing JIRA connection..."
python test_jira_connection.py

# Ask user if they want to proceed with fetching issues
read -p "Do you want to proceed with fetching issues? (y/n): " answer

if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
    echo "Running fixed JIRA client..."
    python jira_client_fixed.py
else
    echo "Exiting without fetching issues."
fi 
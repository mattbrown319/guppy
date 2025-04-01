#!/bin/bash

# This script ensures that the same Python environment that has the dependencies installed is used to run the script

# First, determine the Python executable that has the packages installed
PYTHON_PATH=$(which python3)

# Install requirements if not already installed
$PYTHON_PATH -m pip install -r requirements.txt

# Run the JIRA client
$PYTHON_PATH jira_client.py 
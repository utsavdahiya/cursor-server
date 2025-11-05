#!/bin/bash
# Run script that ensures the virtual environment is used

set -e

# Activate virtual environment
source ~/dev-tools/myenv/bin/activate

# Run the server
python main.py "$@"



#!/bin/bash

# Name of the virtual environment folder
VENV_DIR="venv"

# Create a virtual environment
python3 -m venv $VENV_DIR

# Activate the virtual environment
source $VENV_DIR/bin/activate

# Install the requirements
python3 metatron3.py

#!/bin/bash
# Setup script for Cursor API Server
# This script activates the virtual environment and installs dependencies

set -e

# Activate virtual environment
echo "Activating virtual environment at ~/dev-tools/myenv..."
source ~/dev-tools/myenv/bin/activate

# Verify Python version
echo "Python version: $(python --version)"
echo "Python path: $(which python)"

# Install/upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install Cursor Agent CLI
echo "Installing Cursor Agent CLI..."
if ! command -v cursor-agent >/dev/null 2>&1; then
    echo "Cursor Agent not found. Installing..."
    curl https://cursor.com/install -fsS | bash
    if [ $? -eq 0 ]; then
        echo "✅ Cursor Agent installed successfully"
        # Add ~/.local/bin to PATH if not already present
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            export PATH="$HOME/.local/bin:$PATH"
            echo "✅ Added ~/.local/bin to PATH"
        fi
    else
        echo "⚠️  Warning: Cursor Agent installation may have failed. You can manually install it later."
    fi
else
    echo "✅ Cursor Agent already installed"
fi

# Ensure ~/.local/bin is in PATH for this session
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
    echo "✅ Added ~/.local/bin to PATH"
fi

# Install project dependencies
echo "Installing project dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the server:"
echo "  1. Activate the environment: source ~/dev-tools/myenv/bin/activate"
echo "  2. Run the server: python main.py"
echo ""
echo "Optional: Set environment variables:"
echo "  export CURSOR_API_KEY=your_api_key_here  # Get from https://cursor.com/settings"
echo "  export CURSOR_WORKSPACE=/path/to/your/project"
echo "  export PORT=8000  # Default is 8000"
echo "  export HOST=0.0.0.0  # Default is 0.0.0.0"



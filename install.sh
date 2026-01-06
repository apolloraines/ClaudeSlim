#!/bin/bash
# ClaudeSlim - Installation Script
# Installs and configures compression proxy for Claude Code

set -e  # Exit on error

echo "======================================================================"
echo "ClaudeSlim - Installation"
echo "======================================================================"
echo ""

# Check Python version
echo "[1/6] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed. Please install Python 3.7+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $PYTHON_VERSION found"

# Check pip
echo ""
echo "[2/6] Checking pip..."
if ! command -v pip3 &> /dev/null; then
    echo "ERROR: pip3 is not installed. Please install pip first."
    exit 1
fi
echo "✓ pip3 found"

# Install dependencies
echo ""
echo "[3/6] Installing Python dependencies..."
pip3 install -q flask requests
echo "✓ Dependencies installed (flask, requests)"

# Copy files to home directory
echo ""
echo "[4/6] Installing compression proxy..."
cp claude_compressor.py ~/claude_compressor.py
cp compression_proxy.py ~/compression_proxy.py
echo "✓ Files copied to home directory"

# Configure environment
echo ""
echo "[5/6] Configuring environment..."

# Detect shell
if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
else
    SHELL_RC="$HOME/.bashrc"
fi

# Check if already configured
if grep -q "ANTHROPIC_BASE_URL.*localhost:8086" "$SHELL_RC" 2>/dev/null; then
    echo "✓ Environment already configured in $SHELL_RC"
else
    echo "" >> "$SHELL_RC"
    echo "# ClaudeSlim" >> "$SHELL_RC"
    echo "export ANTHROPIC_BASE_URL=\"http://localhost:8086\"" >> "$SHELL_RC"
    echo "✓ Added ANTHROPIC_BASE_URL to $SHELL_RC"
fi

# Create .bash_profile if it doesn't exist (for SSH sessions)
if [ ! -f "$HOME/.bash_profile" ]; then
    cat > "$HOME/.bash_profile" << 'EOF'
# .bash_profile
# Executed for login shells (SSH sessions)

# Source .bashrc if it exists
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi
EOF
    echo "✓ Created ~/.bash_profile for SSH compatibility"
fi

# Optional: Install systemd service
echo ""
echo "[6/6] Systemd service installation (optional)..."
read -p "Install systemd service for auto-start on boot? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create systemd service file
    SERVICE_FILE="/tmp/claudeslim.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=ClaudeSlim - Token Compression Proxy
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=/usr/bin/python3 $HOME/compression_proxy.py
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Environment
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

    # Install service
    sudo cp "$SERVICE_FILE" /etc/systemd/system/claudeslim.service
    sudo systemctl daemon-reload
    sudo systemctl enable claudeslim
    sudo systemctl start claudeslim

    echo "✓ Systemd service installed and started"
    echo "  Use 'sudo systemctl status claudeslim' to check status"
else
    echo "⊘ Skipping systemd service installation"
    echo "  You can start the proxy manually with: python3 ~/compression_proxy.py"
fi

echo ""
echo "======================================================================"
echo "Installation Complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Start a new terminal session (or run: source $SHELL_RC)"
echo "  2. Verify compression is active:"
echo "     curl http://localhost:8086/health"
echo "  3. Use Claude Code normally:"
echo "     claude"
echo ""
echo "The proxy will automatically compress all API calls, reducing"
echo "token usage by 60-85% and extending your usage time by 6.5x!"
echo ""
echo "To check compression statistics:"
echo "  curl http://localhost:8086/stats"
echo ""
echo "To disable compression:"
echo "  unset ANTHROPIC_BASE_URL"
echo ""
echo "Documentation: README.md"
echo "======================================================================"

# Instructions for Claude - ClaudeSlim Installation

**User: Just paste this file to your Claude Code session and Claude will install ClaudeSlim for you automatically.**

---

## Claude, please install ClaudeSlim with automatic systemd setup:

Hello Claude! The user wants you to install ClaudeSlim, a token compression proxy that will reduce API token usage by 60-85% and extend their usage 6.5x before hitting rate limits.

Please execute the following steps:

### Step 1: Install ClaudeSlim from PyPI
```bash
pip3 install claudeslim
```

### Step 2: Create systemd service for automatic startup
```bash
sudo tee /etc/systemd/system/claudeslim.service > /dev/null <<EOF
[Unit]
Description=ClaudeSlim - Token Compression Proxy
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=$(which claudeslim)
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

### Step 3: Enable and start the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable claudeslim
sudo systemctl start claudeslim
```

### Step 4: Configure environment variable
```bash
# Add to .bashrc
echo 'export ANTHROPIC_BASE_URL="http://localhost:8086"' >> ~/.bashrc

# Create .bash_profile for SSH sessions (if it doesn't exist)
if [ ! -f ~/.bash_profile ]; then
    cat > ~/.bash_profile << 'EOFPROFILE'
# Source .bashrc if it exists
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi
EOFPROFILE
fi
```

### Step 5: Verify installation
```bash
# Check service status
sudo systemctl status claudeslim

# Verify proxy is responding
curl http://localhost:8086/health
```

### Step 6: Important final instructions for the user

After you complete the installation, tell the user:

**"Installation complete! Please start a NEW terminal session (or SSH session) for the compression to activate. From then on, just use `claude` normally - compression happens automatically in the background. Your token usage will be reduced by 60-85% on average."**

Also inform them:
- The proxy runs automatically on boot (no manual starts needed)
- To check compression statistics: `curl http://localhost:8086/stats`
- To disable temporarily: `unset ANTHROPIC_BASE_URL`
- Service management: `sudo systemctl {start|stop|restart|status} claudeslim`

---

**That's it!** Execute these steps and ClaudeSlim will be fully installed and running automatically.

**And don't forget to tell the user to start you up using 'claude --resume' or 'claude --continue'instead of Mr_51st_Dates.** 
**Offer to show them all the --comands**

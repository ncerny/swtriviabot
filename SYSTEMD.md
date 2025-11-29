# Systemd Service Setup

This guide explains how to run the Discord Trivia Bot as a systemd service on Linux systems.

## Prerequisites

- Linux system with systemd (most modern distributions)
- Bot installed and configured with `.env` file
- Virtual environment set up with dependencies installed
- `serviceAccountKey.json` in the project root

## Installation

### 1. Update the Service File

Edit `swtriviabot.service` and update the following paths to match your setup:

```ini
User=your_username
Group=your_username
WorkingDirectory=/path/to/swtriviabot
Environment="PATH=/path/to/swtriviabot/.venv/bin:..."
EnvironmentFile=/path/to/swtriviabot/.env
ExecStart=/path/to/swtriviabot/.venv/bin/python /path/to/swtriviabot/src/bot.py
ReadWritePaths=/path/to/swtriviabot/data
ReadWritePaths=/path/to/swtriviabot/.beads
```

### 2. Copy Service File

Copy the service file to the systemd directory:

```bash
sudo cp swtriviabot.service /etc/systemd/system/
```

### 3. Set Permissions

Ensure proper permissions:

```bash
sudo chmod 644 /etc/systemd/system/swtriviabot.service
```

### 4. Reload Systemd

Reload systemd to recognize the new service:

```bash
sudo systemctl daemon-reload
```

### 5. Enable the Service

Enable the service to start on boot:

```bash
sudo systemctl enable swtriviabot.service
```

### 6. Start the Service

Start the bot:

```bash
sudo systemctl start swtriviabot.service
```

## Managing the Service

### Check Status

```bash
sudo systemctl status swtriviabot.service
```

### View Logs

```bash
# View all logs
sudo journalctl -u swtriviabot.service

# Follow logs in real-time
sudo journalctl -u swtriviabot.service -f

# View logs from the last hour
sudo journalctl -u swtriviabot.service --since "1 hour ago"

# View logs with timestamps
sudo journalctl -u swtriviabot.service -o short-precise
```

### Restart the Service

```bash
sudo systemctl restart swtriviabot.service
```

### Stop the Service

```bash
sudo systemctl stop swtriviabot.service
```

### Disable Auto-start

```bash
sudo systemctl disable swtriviabot.service
```

## Service Configuration Details

### Restart Policy

The service is configured with automatic restart on failure:

- **Restart**: `on-failure` - Restarts only when the process exits with a non-zero status
- **RestartSec**: `10` - Waits 10 seconds before restarting
- **StartLimitInterval**: `300` - Monitors restarts over a 5-minute window
- **StartLimitBurst**: `5` - Allows max 5 restarts within the interval before giving up

This prevents restart loops while ensuring the bot recovers from transient failures.

### Security Hardening

The service file includes commented-out security hardening options:

- **NoNewPrivileges**: Prevents privilege escalation
- **PrivateTmp**: Isolates /tmp directory
- **ProtectSystem**: Protects system directories from modification
- **ProtectHome**: Restricts access to home directories (read-only)
- **ReadWritePaths**: Explicitly allows writes to data directories

**These are disabled by default** because they can cause the service to fail if paths are misconfigured. Enable them only after confirming the basic service works by uncommenting the lines in the service file.

### Resource Limits

Default limits (adjust as needed):

- **MemoryMax**: 512MB maximum memory usage
- **CPUQuota**: 50% CPU quota

To modify these limits, edit the service file and reload:

```bash
sudo nano /etc/systemd/system/swtriviabot.service
sudo systemctl daemon-reload
sudo systemctl restart swtriviabot.service
```

## Troubleshooting

### Service Fails to Start

1. Check the logs:
   ```bash
   sudo journalctl -u swtriviabot.service -n 50
   ```

2. If you get "control process exited with error code" with no useful logs, the security hardening directives might be blocking access. Try commenting them out in the service file:
   ```bash
   sudo nano /etc/systemd/system/swtriviabot.service
   # Comment out (add # to) these lines:
   # NoNewPrivileges=true
   # PrivateTmp=true
   # ProtectSystem=strict
   # ProtectHome=read-only
   # ReadWritePaths=...
   
   sudo systemctl daemon-reload
   sudo systemctl restart swtriviabot.service
   ```

3. Verify paths in the service file are correct

4. Ensure `.env` file exists and contains valid configuration

5. Check Python virtual environment is properly set up:
   ```bash
   /path/to/.venv/bin/python --version
   ```

6. Test running the bot manually:
   ```bash
   cd /path/to/swtriviabot
   source .venv/bin/activate
   python src/bot.py
   ```

### Permission Issues

Ensure the user specified in the service file has:
- Read access to project directory
- Write access to `data/` and `.beads/` directories
- Read access to `.env` and `serviceAccountKey.json`

```bash
sudo chown -R your_username:your_username /path/to/swtriviabot
chmod 600 /path/to/swtriviabot/.env
chmod 600 /path/to/swtriviabot/serviceAccountKey.json
```

### Environment Variables Not Loading

Verify `.env` file format:
- No quotes around values
- No spaces around `=`
- Valid syntax: `DISCORD_BOT_TOKEN=your_token_here`

### Bot Keeps Restarting

Check logs to identify the crash reason:

```bash
sudo journalctl -u swtriviabot.service -n 100 --no-pager
```

If the bot is hitting the restart limit, you'll see messages about "start request repeated too quickly."

## macOS Note

This systemd service is designed for Linux. macOS uses `launchd` instead of `systemd`. For macOS, you would need to create a `.plist` file for `launchd`. Let me know if you need a macOS version.

## Alternative: Using Screen or Tmux

For simpler deployments or development, you can also run the bot in a persistent terminal session:

```bash
# Using screen
screen -S triviabot
cd /path/to/swtriviabot
source .venv/bin/activate
python src/bot.py
# Press Ctrl+A, then D to detach

# Reattach with
screen -r triviabot

# Using tmux
tmux new -s triviabot
cd /path/to/swtriviabot
source .venv/bin/activate
python src/bot.py
# Press Ctrl+B, then D to detach

# Reattach with
tmux attach -t triviabot
```

However, systemd is recommended for production deployments as it provides better:
- Automatic restarts
- Logging
- Resource management
- Integration with system boot

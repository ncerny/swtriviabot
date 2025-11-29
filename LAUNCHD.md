# macOS launchd Service Setup

This guide explains how to run the Discord Trivia Bot as a launchd service on macOS.

## Prerequisites

- macOS system
- Bot installed and configured with `.env` file
- Virtual environment set up with dependencies installed
- `serviceAccountKey.json` in the project root

## Installation

### 1. Create Logs Directory

Create a directory for log files:

```bash
mkdir -p /Users/ncerny/workspace/swtriviabot/logs
```

### 2. Update the Plist File (if needed)

The provided `com.ncerny.swtriviabot.plist` is already configured for your setup. If you need to modify paths, edit the plist file.

### 3. Load Environment Variables

Since launchd doesn't automatically load `.env` files, you have two options:

**Option A: Modify bot.py to load .env** (Recommended)

Add this to the top of `src/bot.py` if not already present:

```python
from dotenv import load_dotenv
load_dotenv()  # This loads .env file
```

**Option B: Add environment variables to plist**

Edit the plist file to include your environment variables:

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>PATH</key>
    <string>...</string>
    <key>DISCORD_BOT_TOKEN</key>
    <string>your_token_here</string>
    <key>DEV_MODE</key>
    <string>false</string>
</dict>
```

⚠️ **Option A is recommended** as it keeps secrets out of the plist file.

### 4. Copy Plist to LaunchAgents

Copy the plist file to your LaunchAgents directory:

```bash
cp com.ncerny.swtriviabot.plist ~/Library/LaunchAgents/
```

### 5. Set Permissions

Ensure proper permissions:

```bash
chmod 644 ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist
```

### 6. Load the Service

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist
```

### 7. Start the Service

Start the bot:

```bash
launchctl start com.ncerny.swtriviabot
```

## Managing the Service

### Check Status

```bash
launchctl list | grep swtriviabot
```

### View Logs

```bash
# View stdout logs
tail -f /Users/ncerny/workspace/swtriviabot/logs/stdout.log

# View stderr logs
tail -f /Users/ncerny/workspace/swtriviabot/logs/stderr.log

# View both
tail -f /Users/ncerny/workspace/swtriviabot/logs/*.log
```

### Restart the Service

```bash
launchctl stop com.ncerny.swtriviabot
launchctl start com.ncerny.swtriviabot
```

Or restart in one command:

```bash
launchctl kickstart -k gui/$(id -u)/com.ncerny.swtriviabot
```

### Stop the Service

```bash
launchctl stop com.ncerny.swtriviabot
```

### Unload the Service

To completely unload (disable auto-start):

```bash
launchctl unload ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist
```

### Reload After Editing

If you modify the plist file:

```bash
launchctl unload ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist
launchctl load ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist
```

## Service Configuration Details

### Restart Policy

The service is configured with automatic restart on failure:

- **RunAtLoad**: Starts automatically when loaded (at login)
- **KeepAlive**: Restarts if crashes or exits unsuccessfully
- **ThrottleInterval**: Waits 10 seconds before restarting after a crash

This prevents restart loops while ensuring the bot recovers from failures.

### Key Configuration Options

- **Label**: Unique identifier for the service
- **ProgramArguments**: Command and arguments to run
- **WorkingDirectory**: Directory to run from
- **StandardOutPath/StandardErrorPath**: Log file locations
- **ProcessType**: Set to `Interactive` for user-level services

## Troubleshooting

### Service Fails to Start

1. Check the logs:
   ```bash
   cat /Users/ncerny/workspace/swtriviabot/logs/stderr.log
   ```

2. Verify the plist is valid:
   ```bash
   plutil -lint ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist
   ```

3. Check if the service is loaded:
   ```bash
   launchctl list | grep swtriviabot
   ```

4. Test running the bot manually:
   ```bash
   cd /Users/ncerny/workspace/swtriviabot
   source .venv/bin/activate
   python src/bot.py
   ```

### Environment Variables Not Loading

Ensure `python-dotenv` is installed and `.env` is being loaded:

```bash
source .venv/bin/activate
pip show python-dotenv
```

If not installed:

```bash
pip install python-dotenv
```

### Permission Issues

Ensure you have read/write access:

```bash
ls -la /Users/ncerny/workspace/swtriviabot/.env
ls -la /Users/ncerny/workspace/swtriviabot/serviceAccountKey.json
```

Logs directory must be writable:

```bash
ls -la /Users/ncerny/workspace/swtriviabot/logs
```

### Bot Keeps Restarting

Check stderr logs to identify the crash reason:

```bash
tail -n 100 /Users/ncerny/workspace/swtriviabot/logs/stderr.log
```

### Service Doesn't Start at Login

Ensure the plist is in the correct location:

```bash
ls -l ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist
```

Check that `RunAtLoad` is set to `true` in the plist.

### Viewing Console Logs

You can also view logs in macOS Console app:

1. Open Console.app
2. Search for "swtriviabot"
3. Filter by your user or process

## Quick Reference

```bash
# Load service (enable)
launchctl load ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist

# Unload service (disable)
launchctl unload ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist

# Start service
launchctl start com.ncerny.swtriviabot

# Stop service
launchctl stop com.ncerny.swtriviabot

# Restart service
launchctl kickstart -k gui/$(id -u)/com.ncerny.swtriviabot

# Check status
launchctl list | grep swtriviabot

# View logs
tail -f ~/workspace/swtriviabot/logs/*.log

# Validate plist syntax
plutil -lint ~/Library/LaunchAgents/com.ncerny.swtriviabot.plist
```

## Differences from Linux systemd

- launchd uses `.plist` XML files instead of `.service` unit files
- Services go in `~/Library/LaunchAgents/` (user) or `/Library/LaunchDaemons/` (system)
- No built-in journaling like systemd's journalctl - uses log files instead
- `RunAtLoad` replaces systemd's `WantedBy=multi-user.target`
- `KeepAlive` replaces systemd's `Restart=on-failure`

## Alternative: Using Screen or Tmux

For simpler deployments or development:

```bash
# Using screen
screen -S triviabot
cd ~/workspace/swtriviabot
source .venv/bin/activate
python src/bot.py
# Press Ctrl+A, then D to detach

# Using tmux
tmux new -s triviabot
cd ~/workspace/swtriviabot
source .venv/bin/activate
python src/bot.py
# Press Ctrl+B, then D to detach
```

However, launchd is recommended for production as it provides automatic restarts and starts at login.

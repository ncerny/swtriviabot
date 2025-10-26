# Deployment Guide: Discord Trivia Bot

This guide covers deploying the Discord Trivia Bot using production artifacts from GitHub Releases or from source code.

## Prerequisites

- Discord bot token (see [README.md](README.md) for setup instructions)
- Hosting platform account (pella.app recommended)
- (Optional) Git repository access for source deployment

---

## Quick Deploy: Using Release Artifacts (Recommended)

GitHub Actions automatically creates production-ready artifacts for each release. These are smaller, faster to deploy, and contain only the code needed to run the bot.

### 1. Download the Latest Release

1. Go to [GitHub Releases](https://github.com/ncerny/swtriviabot/releases)
2. Download the `.tar.gz` artifact from the latest release
3. Extract on your server:

```bash
# Download (replace VERSION with actual version, e.g., v1.2.3)
curl -LO https://github.com/ncerny/swtriviabot/releases/download/VERSION/swtriviabot-VERSION.tar.gz

# Extract
tar -xzf swtriviabot-VERSION.tar.gz
cd swtriviabot-VERSION
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Bot Token

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your token
# DISCORD_BOT_TOKEN=your_token_here
```

### 4. Run the Bot

```bash
python -m src.bot
```

**Advantages of Artifact Deployment:**
- ✅ 30-50% smaller download (no tests, docs, or dev tools)
- ✅ Faster deployment (fewer files to transfer)
- ✅ Production-ready (only runtime code included)
- ✅ Verified by CI/CD (all tests passed before release)

---

## Deploying to pella.app

### Option A: From Release Artifact (Recommended)

1. Download artifact to your local machine (see above)
2. Create pella.app application from local directory
3. Upload extracted artifact contents
4. Configure environment and volumes (see below)

### Option B: From Git Repository

Ensure your repository has the following files:

- `requirements.txt` - Python dependencies
- `Procfile` - Contains: `bot: python src/bot.py`
- `.env.example` - Template for environment variables
- `src/bot.py` - Main bot entry point

### pella.app Configuration

1. **Create Application**
   - Go to [pella.app](https://pella.app) and sign up/log in
   - Click "New Application"
   - Connect your Git repository OR upload artifact

2. **Environment Variables**
   - Go to "Settings" → "Environment Variables"
   - Add `DISCORD_BOT_TOKEN` with your bot token value
   - Save changes

3. **Persistent Storage**
   - Go to "Settings" → "Volumes"
   - Add volume: `/app/data` (100MB)
   - Save changes

4. **Deploy**
   - Click "Deploy"
   - Monitor logs for confirmation:
     - ✅ Bot logged in successfully
     - 📂 Sessions loaded from disk
     - 🔄 Commands synced with Discord

---

## Deploying to Other Platforms

### Railway.app

1. Create new project from GitHub repo
2. Add environment variable: `DISCORD_BOT_TOKEN`
3. Configure volume mount:
   - Path: `/app/data`
   - Size: 100MB
4. Deploy using `Procfile` configuration

### Heroku

1. Create new Heroku app
2. Connect GitHub repository
3. Add buildpack: `heroku/python`
4. Add environment variable: `DISCORD_BOT_TOKEN`
5. Enable Heroku Postgres (free tier) or use disk storage addon
6. Deploy from branch

### Docker Container

1. Create `Dockerfile`:

```dockerfile
# Use Python 3.13 slim image for minimal size
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Create data directory for persistence
RUN mkdir -p /app/data

CMD ["python", "src/bot.py"]
```

2. Build image:

```bash
docker build -t discord-trivia-bot .
```

3. Run container:

```bash
docker run -d \
  --name trivia-bot \
  -e DISCORD_BOT_TOKEN=your_token_here \
  -v /path/to/data:/app/data \
  discord-trivia-bot
```

---

## Monitoring and Maintenance

### Check Bot Status

Monitor application logs for:

- ✅ Successful login messages
- 📂 Session load/save operations
- ❌ Error messages
- 🔄 Command execution logs

### Update Bot

1. Push changes to your Git repository
2. Deploy from pella.app dashboard
3. Bot will restart automatically

### Backup Session Data

Session data is stored in `/data/*.json` files:

1. Access your hosting platform's file browser
2. Download all `.json` files from `/data/` directory
3. Store backups securely

### Restore Session Data

1. Upload backed-up `.json` files to `/data/` directory
2. Restart the bot
3. Sessions will be loaded automatically on startup

---

## Troubleshooting

### Bot Not Responding to Commands

1. **Check bot is online**: Look for green status in Discord server
2. **Verify permissions**: Bot needs `Send Messages` permission
3. **Check logs**: Look for error messages in hosting platform logs
4. **Resync commands**: Restart bot to trigger command sync

### Commands Not Appearing

1. **Check bot invite**: Ensure bot was invited with `applications.commands` scope
2. **Wait for sync**: Commands can take up to 1 hour to appear globally
3. **Use guild commands**: For testing, register commands per-server

### Permission Errors

1. **Admin commands**: `/list-answers` and `/reset-answers` require Administrator permission
2. **Bot permissions**: Ensure bot has necessary server permissions
3. **User permissions**: Verify user has correct roles

### Data Loss

1. **Check volume mount**: Ensure `/data/` directory is properly mounted
2. **Verify file writes**: Check logs for "Saved X session(s)" messages
3. **Restore from backup**: Use backup `.json` files if needed

---

## Performance Optimization

### Memory Usage

- **Current**: ~50MB base + ~10KB per active guild session
- **Target**: <100MB total for 100 guilds
- **Monitor**: Check memory usage in platform dashboard

### Response Times

- **Target**: <2s p95 for `/answer`, <3s for `/list-answers`, <1s for `/reset-answers`
- **Monitor**: Check application logs for command execution times

### Cost Optimization

- **pella.app**: ~$3-5/month for basic instance
- **Storage**: 100MB volume sufficient for ~10,000 sessions
- **Scaling**: Bot handles 100+ concurrent users on single instance

---

## Security Best Practices

1. **Never commit** `.env` file or bot token to Git
2. **Use environment variables** for all secrets
3. **Limit permissions**: Grant bot minimum required permissions
4. **Monitor logs**: Watch for unusual activity
5. **Regular updates**: Keep dependencies up to date

---

## Support

For issues or questions:

1. Check logs for error messages
2. Review [README.md](README.md) for setup instructions
3. Consult [quickstart.md](specs/001-discord-trivia-bot/quickstart.md) for development guide
4. Open an issue on GitHub

---

**Deployment Status**: ✅ Ready for production

**Hosting Cost**: <$5/month (pella.app)

**Uptime Target**: 99.9%

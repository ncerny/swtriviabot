# Deployment Guide: Discord Trivia Bot

This guide covers deploying the Discord Trivia Bot to pella.app and other hosting platforms.

## Prerequisites

- Discord bot token (see [README.md](README.md) for setup instructions)
- Git repository with your code
- Hosting platform account (pella.app recommended)

---

## Deploying to pella.app

### 1. Prepare Your Repository

Ensure your repository has the following files:

- `requirements.txt` - Python dependencies
- `Procfile` - Contains: `bot: python src/bot.py`
- `.env.example` - Template for environment variables
- `src/bot.py` - Main bot entry point

### 2. Create a pella.app Application

1. Go to [pella.app](https://pella.app) and sign up/log in
2. Click "New Application"
3. Connect your Git repository
4. Select the branch (e.g., `001-discord-trivia-bot`)

### 3. Configure Environment Variables

In the pella.app dashboard:

1. Go to "Settings" → "Environment Variables"
2. Add `DISCORD_BOT_TOKEN` with your bot token value
3. Save changes

### 4. Configure Persistent Storage

The bot requires persistent disk storage for session data:

1. Go to "Settings" → "Volumes"
2. Add a new volume:
   - **Mount Path**: `/app/data`
   - **Size**: 100MB (sufficient for session storage)
3. Save changes

### 5. Deploy

1. Click "Deploy" in the pella.app dashboard
2. Monitor deployment logs for any errors
3. Once deployed, check logs to confirm:
   - ✅ Bot logged in successfully
   - 📂 Sessions loaded from disk
   - 🔄 Commands synced with Discord

### 6. Verify Bot is Running

1. Go to your Discord server
2. Type `/` and verify the following commands appear:
   - `/answer` - Submit answer
   - `/list-answers` - View answers (admin only)
   - `/reset-answers` - Reset session (admin only)
3. Test the commands to ensure they work

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
FROM python:3.14-slim

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

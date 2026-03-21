# Docker Setup for YouTube Auto-Refresh

## Problem
After 2-3 days in production, YouTube cookies expire and the auto-refresh system attempts to refresh them. However, if the refresher script is not included in your Docker image, you'll see:

```
ERROR: Auto-refresh script not found at any of: [...]
Ensure scripts/refresh_youtube_cookies.py is included in your Docker image.
```

## Solution
Update your Dockerfile to include the scripts and Playwright dependencies.

### Dockerfile Changes

Add these lines to your Dockerfile **after** your base Python image and before `pip install`:

```dockerfile
# Copy the refresher scripts
COPY scripts/refresh_youtube_cookies.py /app/scripts/
COPY scripts/setup_youtube_profile.py /app/scripts/

# Install Playwright and browser dependencies
RUN pip install playwright && \
    python3 -m playwright install
```

### Complete Example
Here's a typical production Dockerfile with auto-refresh support:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libpango-gobject-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY backend/requirements.txt .

# Install Python dependencies including Playwright
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install playwright && \
    python3 -m playwright install

# Copy the refresher scripts
COPY scripts/refresh_youtube_cookies.py /app/scripts/
COPY scripts/setup_youtube_profile.py /app/scripts/

# Copy the rest of the application
COPY . .

# Expose port and run the app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Verifying Setup

After rebuilding and redeploying your Docker image, verify the auto-refresh script is present:

```bash
# SSH into your container
docker exec -it <container_id> bash

# Check if the script exists
ls -la /app/scripts/refresh_youtube_cookies.py

# Check if Playwright is installed
python3 -c "import playwright; print('Playwright OK')"
```

## How Auto-Refresh Works

1. **Cookie Expiration**: After ~2-3 days, YouTube requires re-authentication
2. **Detection**: When yt-dlp hits a "Sign in to confirm" error, the backend detects this
3. **Rate Limit**: Auto-refresh attempts are limited to 1 per job per hour to avoid spam
4. **Script Execution**: `refresh_youtube_cookies.py` uses Playwright to:
   - Launch a Chrome browser (headless in production)
   - Load YouTube in the persistent profile
   - Perform manual login if needed (or use cached session)
   - Export updated cookies back to the environment
5. **Retry**: yt-dlp retries the download with refreshed cookies

## Environment Variables

Ensure these are set in your deployment:

```bash
# Enable auto-refresh on bot-check errors
YOUTUBE_ENABLE_AUTO_REFRESH=true

# Persistent profile directory (should be a volume in Docker)
YOUTUBE_BROWSER_PROFILE_DIR=/data/youtube_profile

# Where to write refreshed cookies
YOUTUBE_AUTO_REFRESH_OUT=/tmp/youtube_cookies.txt

# Run browser headless in production
YOUTUBE_AUTO_REFRESH_HEADLESS=true
```

## Troubleshooting

### Script still not found after update?
- Verify the `COPY` commands in Dockerfile are correct
- Rebuild the image: `docker build -t my-app:latest .`
- Check file permissions in the image

### Playwright install fails?
- Ensure system dependencies are installed (see `apt-get install` above)
- Check Docker build logs for specific errors
- Consider using `mcr.microsoft.com/playwright:v1.40.0-focal` as base image instead

### Auto-refresh still failing?
- Check logs: `docker logs <container_id> | grep -i "auto-refresh"`
- Verify YouTube cookies are being exported: `docker exec <container_id> ls -la /tmp/youtube_cookies.txt`
- Ensure `YOUTUBE_BROWSER_PROFILE_DIR` is a mounted volume so profile persists

## Testing Locally

To test auto-refresh before deploying:

```bash
# Activate your virtual environment
source venv/bin/activate

# Run the setup script to create a YouTube profile
python scripts/setup_youtube_profile.py

# Enable auto-refresh in your .env
echo "YOUTUBE_ENABLE_AUTO_REFRESH=true" >> .env

# Start the server
python -m uvicorn backend.main:app --reload

# Monitor logs for auto-refresh activity
```

## Next Steps

1. Update your Dockerfile with the above changes
2. Rebuild and test locally with Docker: `docker build -t myapp:test .`
3. Verify the script exists: `docker run myapp:test ls /app/scripts/`
4. Deploy to production
5. Monitor logs for successful auto-refresh: `YOUTUBE_ENABLE_AUTO_REFRESH=true` in logs after job completes

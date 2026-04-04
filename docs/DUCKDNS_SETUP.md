# DuckDNS Home Proxy Setup for Railway

## Overview
Railway (datacenter) cannot reach your home IP directly. **DuckDNS** provides a stable hostname that points to your dynamic home IP, allowing Railway to route yt-dlp requests through your Tinyproxy.

## Prerequisites
- ✅ Tinyproxy running locally on port 53128 (from previous setup)
- ✅ Port forwarding configured (53128 → your Mac)
- ✅ DuckDNS account at https://www.duckdns.org (free)

## Step 1: Get DuckDNS Token
1. Go to https://www.duckdns.org
2. Sign up (GitHub/Google/email)
3. Copy your **token** from the dashboard
4. Run the setup script:

```bash
chmod +x scripts/setup_duckdns.sh
./scripts/setup_duckdns.sh
```

The script will:
- Prompt for your DuckDNS token and desired subdomain
- Set up automatic IP refresh via cron (every 5 minutes)
- Test Tinyproxy connectivity
- Provide Railway configuration

## Step 2: Configure Railway
After the script completes, set this environment variable on Railway:

```
YTDLP_PROXY_URL=http://railwayproxy:<password>@<subdomain>.duckdns.org:53128
```

Example:
```
YTDLP_PROXY_URL=http://railwayproxy:Basket77.val2@my-home-proxy.duckdns.org:53128
```

## Step 3: Verify Setup

### Test locally
```bash
# Should return your home public IP (176.170.116.202)
curl -x 'http://railwayproxy:<password>@<subdomain>.duckdns.org:53128' https://api.ipify.org
```

### Check DNS resolution
```bash
dig <subdomain>.duckdns.org
# Should show your public IP (176.170.116.202)

nslookup <subdomain>.duckdns.org
```

### Monitor auto-refresh
```bash
tail -f /tmp/duckdns_update.log
```

### Verify cron job
```bash
crontab -l | grep duckdns
```

### Check Tinyproxy is running
```bash
lsof -i :53128
# Should show tinyproxy listening
```

## Troubleshooting

### "DNS resolves to wrong IP"
- Wait 1-2 minutes for propagation
- Check cron job: `crontab -l`
- Manually trigger: `~/.duckdns_update.sh "token" "subdomain"`
- Check logs: `cat /tmp/duckdns_update.log`

### "Proxy connection times out from Railway"
- Verify port forwarding: `curl -x 'http://railwayproxy:<pass>@<subdomain>.duckdns.org:53128' http://example.com`
- Check Tinyproxy logs: `tail /var/log/tinyproxy.log` (or `grep -r tinyproxy /usr/local/var/log`)
- Verify firewall allows port 53128 inbound

### "Tinyproxy rejects connection"
- Check auth in Tinyproxy config: `/usr/local/etc/tinyproxy/tinyproxy.conf`
- Verify user/password in Railway env var match config

### DuckDNS update failing
- Verify token is correct: https://www.duckdns.org/install
- Check internet connection
- Verify curl is available: `which curl`
- Check manual update: `curl -s "https://www.duckdns.org/update?domains=<subdomain>&token=<token>"`

## Architecture Diagram

```
Railway (yt-dlp)
    ↓
  YTDLP_PROXY_URL = http://user:pass@my-proxy.duckdns.org:53128
    ↓
  DNS resolution (duckdns.org) → 176.170.116.202
    ↓
  Your home network (firewall port 53128)
    ↓
  Tinyproxy (localhost:53128)
    ↓
  YouTube (via your home IP)
    ✅ Accepted (not datacenter IP)
```

## Next Steps

1. **Get DuckDNS token**: https://www.duckdns.org
2. **Run setup script**: `./scripts/setup_duckdns.sh`
3. **Update Railway**: Set `YTDLP_PROXY_URL` environment variable
4. **Test**: Trigger a YouTube download on Railway
5. **Monitor**: Check logs for success

## Reference
- DuckDNS: https://www.duckdns.org
- Tinyproxy: http://tinyproxy.github.io/
- yt-dlp proxy docs: https://github.com/yt-dlp/yt-dlp#proxy-settings

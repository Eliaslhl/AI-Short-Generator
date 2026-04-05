# Twitch Download Optimization

## Current Settings

For optimal Twitch VOD download speed, we use **aria2c** with parallel connections:

```
YTDLP_DOWNLOADER=aria2c
YTDLP_DOWNLOADER_ARGS=aria2c:-x16 -j16 -s16 -k1M
YTDLP_CONCURRENT_FRAGMENTS=16
```

## Performance

- **1.2 GB Twitch VOD**: ~14 seconds (88 MB/s)
- **Speed improvement**: -36% vs default yt-dlp

## Explanation of aria2c flags

- `-x16`: Max 16 connections per server
- `-j16`: Max 16 parallel files
- `-s16`: 16 segments per download
- `-k1M`: 1MB minimum per segment

## Railway Configuration

Add these environment variables to Railway:

```
YTDLP_DOWNLOADER=aria2c
YTDLP_DOWNLOADER_ARGS=aria2c:-x16 -j16 -s16 -k1M
YTDLP_CONCURRENT_FRAGMENTS=16
```

Note: `aria2c` must be installed in the Railway container.

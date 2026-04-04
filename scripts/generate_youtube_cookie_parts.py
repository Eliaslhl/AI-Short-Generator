#!/usr/bin/env python3
"""Generate safe YOUTUBE_COOKIES_B64_PART_* values from a Netscape cookies file.

Usage:
  python3 scripts/generate_youtube_cookie_parts.py \
    --input /Users/elias/Downloads/www.youtube.com_cookies.txt \
    --parts 8 \
    --out /tmp/railway_youtube_cookie_parts.env
"""

from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to cookies.txt (Netscape format)")
    parser.add_argument("--parts", type=int, default=8, help="Number of parts to generate")
    parser.add_argument("--out", required=True, help="Output .env-like file path")
    args = parser.parse_args()

    src = Path(args.input)
    out = Path(args.out)

    if not src.exists():
        raise SystemExit(f"Input not found: {src}")
    if args.parts < 1:
        raise SystemExit("--parts must be >= 1")

    raw = src.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    sha_raw = hashlib.sha256(raw).hexdigest()

    part_size = (len(b64) + args.parts - 1) // args.parts
    parts = [b64[i : i + part_size] for i in range(0, len(b64), part_size)]

    # Verify reconstructability
    rebuilt_b64 = "".join(parts)
    rebuilt_raw = base64.b64decode(rebuilt_b64)
    sha_rebuilt = hashlib.sha256(rebuilt_raw).hexdigest()
    if sha_raw != sha_rebuilt:
        raise SystemExit("Integrity check failed while rebuilding base64 parts")

    lines: list[str] = []
    lines.append(f"# SOURCE_FILE={src}")
    lines.append(f"# TOTAL_B64_LEN={len(b64)}")
    lines.append(f"# PARTS={len(parts)}")
    lines.append(f"# PART_SIZE={part_size}")
    lines.append(f"# COOKIES_FILE_SHA256={sha_raw}")
    for i, p in enumerate(parts, 1):
        lines.append(f"# PART_{i}_LEN={len(p)}")
    lines.append("")
    lines.append("# Paste ONLY the value in Railway (right side), not the KEY= prefix")
    for i, p in enumerate(parts, 1):
        lines.append(f"YOUTUBE_COOKIES_B64_PART_{i}={p}")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(f"TOTAL_B64_LEN={len(b64)} PARTS={len(parts)} PART_SIZE={part_size}")
    print(f"COOKIES_FILE_SHA256={sha_raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

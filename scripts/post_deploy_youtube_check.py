#!/usr/bin/env python3
"""Post-deploy diagnostic for YouTube cookies configuration.

What it checks:
1) Reconstructs cookies payload from YOUTUBE_COOKIES_B64_PART_* (or YOUTUBE_COOKIES_B64)
2) Validates base64 decode and Netscape cookies shape
3) Computes SHA256 and compares against expected SHA (CLI or env)
4) Optionally scans a backend log file for known success/failure signals

Usage examples:
  python3 scripts/post_deploy_youtube_check.py \
    --env-file temp/railway_youtube_cookie_parts.env \
    --expected-sha bf39253b28772a86e18ec71c8ade9e272dcc009b0240656aaa94cbb5a933b21d

  python3 scripts/post_deploy_youtube_check.py \
    --env-file temp/railway_youtube_cookie_parts.env \
    --expected-sha <sha256> \
    --log-file /path/to/backend.log
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


PART_PREFIX = "YOUTUBE_COOKIES_B64_PART_"


@dataclass
class CheckResult:
    ok: bool
    details: str


def _sanitize_b64_fragment(value: str) -> str:
    if value is None:
        return ""
    v = value.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    if v.lower().startswith("base64:"):
        v = v.split(":", 1)[1]
    return "".join(v.split())


def _parse_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def _collect_cookie_source(env: Dict[str, str]) -> Tuple[str, Dict[int, str], str | None]:
    indexed: Dict[int, str] = {}
    for key, value in env.items():
        if key.startswith(PART_PREFIX):
            suffix = key[len(PART_PREFIX):]
            try:
                idx = int(suffix)
            except ValueError:
                continue
            indexed[idx] = _sanitize_b64_fragment(value)

    if indexed:
        ordered_indexes = sorted(indexed.keys())
        expected = list(range(1, max(ordered_indexes) + 1))
        if ordered_indexes != expected:
            return "parts", indexed, (
                f"Non-contiguous parts: found {ordered_indexes}, expected contiguous {expected}."
            )
        if any(not indexed[i] for i in ordered_indexes):
            return "parts", indexed, "At least one part value is empty."
        return "parts", indexed, None

    single = _sanitize_b64_fragment(env.get("YOUTUBE_COOKIES_B64", ""))
    if single:
        return "single", {1: single}, None

    return "none", {}, "No YOUTUBE_COOKIES_B64_PART_* or YOUTUBE_COOKIES_B64 found."


def _decode_payload(parts: Dict[int, str]) -> Tuple[bytes | None, str | None, int]:
    b64 = "".join(parts[i] for i in sorted(parts.keys()))
    total_len = len(b64)
    if not b64:
        return None, "Empty reconstructed payload.", total_len

    try:
        return base64.b64decode(b64, validate=True), None, total_len
    except Exception as strict_exc:
        try:
            # permissive fallback for missing padding edge-cases
            return base64.b64decode(b64 + "=", validate=False), None, total_len
        except Exception as permissive_exc:
            return (
                None,
                f"Base64 decode failed (strict={strict_exc}; permissive={permissive_exc})",
                total_len,
            )


def _validate_netscape_shape(decoded: bytes) -> CheckResult:
    try:
        text = decoded.decode("utf-8")
    except Exception as exc:
        return CheckResult(False, f"Decoded bytes are not UTF-8 text: {exc}")

    has_header = "# Netscape HTTP Cookie File" in text
    has_youtube_domain = ".youtube.com" in text or "youtube.com" in text
    if not has_header:
        return CheckResult(False, "Missing Netscape header (# Netscape HTTP Cookie File).")
    if not has_youtube_domain:
        return CheckResult(False, "No youtube.com domain entry detected in decoded cookies.")

    return CheckResult(True, "Netscape shape looks valid (header + youtube domain entries found).")


def _analyze_log_file(path: Path) -> Dict[str, list[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")

    failure_patterns = [
        r"Could not decode YOUTUBE_COOKIES_B64",
        r"YouTube env cookies are present but invalid/undecodable",
        r"decoded cookies sha256 mismatch",
        r"decoded payload is not a valid Netscape YouTube cookies file",
        r"Sign in to confirm you're not a bot",
        r"Bot-check detected and auto-refresh is disabled",
        r"yt-dlp failed",
    ]
    success_patterns = [
        r"YouTube cookies written to",
        r"Using YouTube cookies for download",
        r"\[YTC DEBUG\] cookies file size=.*sha256=",
        r"yt-dlp retry succeeded",
    ]

    failures: list[str] = []
    successes: list[str] = []

    for p in failure_patterns:
        if re.search(p, text, flags=re.IGNORECASE):
            failures.append(p)
    for p in success_patterns:
        if re.search(p, text, flags=re.IGNORECASE):
            successes.append(p)

    return {"failures": failures, "successes": successes}


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-deploy YouTube cookies/env/log diagnostic")
    parser.add_argument("--env-file", type=Path, help="Optional .env-like file to validate")
    parser.add_argument("--expected-sha", help="Expected SHA256 of decoded cookies payload")
    parser.add_argument("--log-file", type=Path, help="Optional backend log file to scan")
    args = parser.parse_args()

    merged_env = dict(os.environ)
    if args.env_file:
        if not args.env_file.exists():
            print(f"[FAIL] env file not found: {args.env_file}")
            return 2
        merged_env.update(_parse_env_file(args.env_file))

    source_mode, parts, collect_error = _collect_cookie_source(merged_env)
    if collect_error:
        print(f"[FAIL] Source detection error: {collect_error}")
        return 2

    part_lens = [len(parts[i]) for i in sorted(parts.keys())]
    print(f"[INFO] source={source_mode} part_count={len(parts)} part_lens={part_lens}")

    decoded, decode_error, total_len = _decode_payload(parts)
    print(f"[INFO] reconstructed_base64_total_len={total_len}")
    if decode_error or decoded is None:
        print(f"[FAIL] {decode_error}")
        return 2

    actual_sha = hashlib.sha256(decoded).hexdigest().lower()
    print(f"[INFO] decoded_size={len(decoded)} sha256={actual_sha}")

    expected_sha = (args.expected_sha or merged_env.get("YOUTUBE_COOKIES_SHA256", "")).strip().lower()
    if expected_sha:
        if expected_sha != actual_sha:
            print(f"[FAIL] SHA mismatch: expected={expected_sha} actual={actual_sha}")
            return 2
        print("[PASS] SHA256 matches expected value.")
    else:
        print("[WARN] No expected SHA provided (use --expected-sha or YOUTUBE_COOKIES_SHA256).")

    shape_result = _validate_netscape_shape(decoded)
    if not shape_result.ok:
        print(f"[FAIL] {shape_result.details}")
        return 2
    print(f"[PASS] {shape_result.details}")

    if args.log_file:
        if not args.log_file.exists():
            print(f"[FAIL] log file not found: {args.log_file}")
            return 2
        report = _analyze_log_file(args.log_file)
        print(f"[INFO] log success signals: {len(report['successes'])}")
        print(f"[INFO] log failure signals: {len(report['failures'])}")
        if report["successes"]:
            print("[INFO] matched success patterns:")
            for p in report["successes"]:
                print(f"  - {p}")
        if report["failures"]:
            print("[FAIL] matched failure patterns:")
            for p in report["failures"]:
                print(f"  - {p}")
            return 2

    print("[PASS] Post-deploy YouTube cookie check is clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
共通の定数定義
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

# ──────────────────────────────────────────────
# タイムゾーン設定
# ──────────────────────────────────────────────
JST = ZoneInfo("Asia/Tokyo")

# ──────────────────────────────────────────────
# パス定義
# ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
STATE_FILE = DATA_DIR / "last_submission_ids.json"
STREAK_FILE = DATA_DIR / "streak.json"

# ──────────────────────────────────────────────
# API設定
# ──────────────────────────────────────────────
SUBMISSIONS_API = "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions"

# ──────────────────────────────────────────────
# Slack設定
# ──────────────────────────────────────────────
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

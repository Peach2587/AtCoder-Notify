"""
Slack通知ユーティリティ
"""

import sys

import requests

from .constants import SLACK_WEBHOOK_URL


def post_to_slack(message: str) -> bool:
    """
    Slack Incoming Webhook にメッセージを送信する。
    
    Args:
        message: 送信するメッセージ文字列
        
    Returns:
        成功時は True、失敗時は False
    """
    if not SLACK_WEBHOOK_URL:
        print("[WARN] SLACK_WEBHOOK_URL が設定されていません。通知をスキップします。", file=sys.stderr)
        return False
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"[INFO] Slack 通知送信: {message}")
        return True
    except requests.RequestException as e:
        print(f"[ERROR] Slack 通知に失敗しました: {e}", file=sys.stderr)
        return False

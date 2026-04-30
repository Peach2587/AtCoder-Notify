"""
Slack通知ユーティリティ
"""

import sys

import requests

from .constants import SLACK_WEBHOOK_URL, SLACK_BOT_TOKEN


def post_to_slack(message: str, channel_id: str | None = None) -> bool:
    """
    Slack にメッセージを送信する。
    channel_id が指定されている場合は Slack Bot API を使用し、
    指定されていない場合は Incoming Webhook を使用する。
    
    Args:
        message: 送信するメッセージ文字列
        channel_id: 送信先チャンネルID（省略時は Webhook でデフォルトチャネルに送信）
        
    Returns:
        成功時は True、失敗時は False
    """
    # チャンネルIDが指定されている場合は Bot API を使用
    if channel_id:
        if not SLACK_BOT_TOKEN:
            print("[WARN] SLACK_BOT_TOKEN が設定されていません。通知をスキップします。", file=sys.stderr)
            return False
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "channel": channel_id,
            "text": message,
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("ok"):
                print(f"[INFO] Slack 通知送信 (channel={channel_id}): {message}")
                return True
            else:
                error = result.get("error", "unknown error")
                print(f"[ERROR] Slack 通知に失敗しました: {error}", file=sys.stderr)
                return False
        except requests.RequestException as e:
            print(f"[ERROR] Slack 通知に失敗しました: {e}", file=sys.stderr)
            return False
    # チャンネルIDが指定されていない場合は Webhook を使用
    else:
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

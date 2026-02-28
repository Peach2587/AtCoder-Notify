"""
AtCoder AC 通知スクリプト
- AtCoder Problems API を使って各メンバーの新規AC提出を検出する
- 新規ACがあれば Slack Incoming Webhook で通知する
- 通知済みの最新提出IDを data/last_submission_ids.json に保存する
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml

# ──────────────────────────────────────────────
# パス設定
# ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
MEMBERS_FILE = REPO_ROOT / "data" / "members.yml"
STATE_FILE = REPO_ROOT / "data" / "last_submission_ids.json"

# AtCoder Problems API
SUBMISSIONS_API = "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions"

# Slack Webhook URL（GitHub Secrets から注入）
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# API リクエスト間のウェイト（レート制限対策）
REQUEST_INTERVAL_SEC = 1.0


# ──────────────────────────────────────────────
# ヘルパー関数
# ──────────────────────────────────────────────

def load_members() -> list[dict]:
    """data/members.yml を読み込んでメンバーリストを返す"""
    with open(MEMBERS_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("members", [])


def load_state() -> dict[str, int]:
    """data/last_submission_ids.json を読み込む。ファイルがなければ空dictを返す"""
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict[str, int]) -> None:
    """data/last_submission_ids.json に状態を保存する"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_submissions(atcoder_id: str, from_second: int) -> list[dict]:
    """
    AtCoder Problems API からユーザーの提出履歴を取得する。
    from_second 以降（Unix 秒）の提出のみ返す。
    """
    params = {"user": atcoder_id, "from_second": from_second}
    try:
        response = requests.get(SUBMISSIONS_API, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] API request failed for {atcoder_id}: {e}", file=sys.stderr)
        return []


def build_slack_message(display_name: str, submission: dict) -> str:
    """Slack 通知用のメッセージ文字列を生成する"""
    contest_id = submission.get("contest_id", "")
    problem_id = submission.get("problem_id", "")
    problem_url = f"https://atcoder.jp/contests/{contest_id}/tasks/{problem_id}"
    # 問題名が取れない場合は problem_id をそのまま表示
    problem_label = problem_id.upper().replace("_", " - ", 1) if problem_id else "不明な問題"
    return (
        f":tada: *{display_name}* が "
        f"<{problem_url}|{problem_label}> を AC しました！"
    )


def post_to_slack(message: str) -> None:
    """Slack Incoming Webhook にメッセージを送信する"""
    if not SLACK_WEBHOOK_URL:
        print("[WARN] SLACK_WEBHOOK_URL が設定されていません。通知をスキップします。", file=sys.stderr)
        return
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"[INFO] Slack 通知送信: {message}")
    except requests.RequestException as e:
        print(f"[ERROR] Slack 通知に失敗しました: {e}", file=sys.stderr)


# ──────────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────────

def main() -> None:
    members = load_members()
    state = load_state()

    # 初回実行時に過去提出を大量通知しないよう、現在時刻の15分前を下限にする
    default_from_second = int(time.time()) - 15 * 60

    for member in members:
        atcoder_id: str = member["atcoder_id"]
        display_name: str = member["display_name"]

        # 前回通知済みの最新提出IDが記録されていれば、その提出の epoch 秒を from_second にする
        # 記録がない場合は default_from_second（現在時刻 - 15分）を使用
        last_id: int = state.get(atcoder_id, 0)
        from_second: int = state.get(f"{atcoder_id}_epoch", default_from_second)

        print(f"[INFO] {atcoder_id} の提出を確認中 (from_second={from_second}) ...")
        submissions = fetch_submissions(atcoder_id, from_second)

        # AC 提出のみ抽出し、提出ID昇順（古い順）に並べる
        ac_submissions = sorted(
            [s for s in submissions if s.get("result") == "AC"],
            key=lambda s: s["id"],
        )

        new_last_id = last_id
        new_last_epoch = from_second

        for sub in ac_submissions:
            if sub["id"] <= last_id:
                # 既に通知済み
                continue
            message = build_slack_message(display_name, sub)
            post_to_slack(message)
            new_last_id = max(new_last_id, sub["id"])
            new_last_epoch = max(new_last_epoch, sub["epoch_second"])

        # 状態を更新
        state[atcoder_id] = new_last_id
        state[f"{atcoder_id}_epoch"] = new_last_epoch

        time.sleep(REQUEST_INTERVAL_SEC)

    save_state(state)
    print("[INFO] 状態ファイルを更新しました。")


if __name__ == "__main__":
    main()

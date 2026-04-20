"""
AtCoder AC 通知スクリプト
- AtCoder Problems API を使って各メンバーの新規AC提出を検出する
- 新規ACがあれば Slack Incoming Webhook で通知する
- その日の初ACの場合は Current Streak Days も通知する
- 通知済みの最新提出IDを data/last_submission_ids.json に保存する
"""

import datetime
import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml

# 親ディレクトリの utils パッケージをインポート
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import hash_id, load_state, save_state, load_streak, save_streak, fetch_submissions, post_to_slack, REPO_ROOT, JST

# ──────────────────────────────────────────────
# パス設定
# ──────────────────────────────────────────────
MEMBERS_FILE = REPO_ROOT / "data" / "members.yml"

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


def build_slack_message(
    display_name: str,
    submission: dict,
    streak: int | None = None,
) -> str:
    """Slack 通知用のメッセージ文字列を生成する"""
    contest_id = submission.get("contest_id", "")
    problem_id = submission.get("problem_id", "")
    problem_url = f"https://atcoder.jp/contests/{contest_id}/tasks/{problem_id}"
    # 問題名が取れない場合は problem_id をそのまま表示
    problem_label = problem_id.upper().replace("_", " - ", 1) if problem_id else "不明な問題"
    msg = (
        f":accepted: *{display_name}* が "
        f"<{problem_url}|{problem_label}> を AC しました！"
    )
    # if streak and streak > 1:
    #     msg += f"\n*Current Streak: {streak+1} days*"
    # else:
    #     msg += f"\n*Current Streak: 1 day*"
    return msg


# ──────────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────────

def main() -> None:
    members = load_members()
    state = load_state()
    streak_state = load_streak()

    today_str = datetime.datetime.now(JST).date().isoformat()

    # 初回実行時に過去提出を大量通知しないよう、現在時刻の15分前を下限にする
    default_from_second = int(time.time()) - 15 * 60

    for member in members:
        atcoder_id: str = member["atcoder_id"]
        display_name: str = member["display_name"]

        # 前回通知済みの最新提出IDが記録されていれば、その提出の epoch 秒を from_second にする
        # 記録がない場合は default_from_second（現在時刻 - 15分）を使用
        # キーは SHA-256 の先頭16桁（生の AtCoder ID を JSON に残さないため）
        hkey = hash_id(atcoder_id)
        last_id: int = state.get(hkey, 0)
        from_second: int = state.get(f"{hkey}_epoch", default_from_second)

        # 本日すでに「初AC通知（ストリーク付き）」を送信済みかどうか
        last_ac_date: str = streak_state.get(f"{hkey}_last_ac_date", "")
        first_ac_today_notified = False

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

            # 提出が今日（JST）のものかどうかを判定
            sub_date = datetime.datetime.fromtimestamp(
                sub["epoch_second"], tz=JST
            ).date().isoformat()

            streak: int | None = None
            if (
                sub_date == today_str
                and last_ac_date != today_str
                and not first_ac_today_notified
            ):
                # 本日初AC → state のメモからストリークを計算
                # 前回のACが昨日なら streak+1、それ以外はリセットして1
                yesterday_str = (
                    datetime.datetime.now(JST).date()
                    - datetime.timedelta(days=1)
                ).isoformat()
                prev_streak: int = streak_state.get(f"{hkey}_streak", 0)
                if last_ac_date == yesterday_str:
                    streak = prev_streak + 1
                else:
                    streak = 1
                print(f"[INFO] {atcoder_id} の本日初AC。streak={streak}")
                streak_state[f"{hkey}_streak"] = streak
                streak_state[f"{hkey}_last_ac_date"] = today_str
                first_ac_today_notified = True

            message = build_slack_message(display_name, sub, streak)
            post_to_slack(message)
            new_last_id = max(new_last_id, sub["id"])
            new_last_epoch = max(new_last_epoch, sub["epoch_second"])

        # 状態を更新
        state[hkey] = new_last_id
        state[f"{hkey}_epoch"] = new_last_epoch

        time.sleep(REQUEST_INTERVAL_SEC)

    save_state(state)
    save_streak(streak_state)
    print("[INFO] 状態ファイルを更新しました。")


if __name__ == "__main__":
    main()

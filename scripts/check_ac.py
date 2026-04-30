"""
AtCoder AC 通知スクリプト
- AtCoder Problems API を使って各メンバーの新規AC提出を検出する
- 新規ACがあれば Slack Incoming Webhook で通知する
- その日の初ACの場合は Current Streak Days も通知する
- 通知済みの最新提出IDを data/last_submission_ids.json に保存する
"""

import argparse
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
from utils import hash_id, load_state, save_state, load_streak, save_streak, fetch_submissions, post_to_slack, load_members, REPO_ROOT, JST

# ──────────────────────────────────────────────
# パス設定
# ──────────────────────────────────────────────
# API リクエスト間のウェイト（レート制限対策）
REQUEST_INTERVAL_SEC = 1.0


# ──────────────────────────────────────────────
# ヘルパー関数
# ──────────────────────────────────────────────

def build_slack_message(
    display_name: str,
    submission: dict,
    streak: int | None = None,
    channel_id: str | None = None,
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
    # その日初めてのAC（streak情報がある）の場合はstreak情報を付加
    if streak is not None:
        msg += f"\nCurrent Streak: {streak} days"
    return msg


def update_streak_for_date(
    hkey: str,
    ac_date: str,
    streak_state: dict,
) -> int:
    """
    指定された日付のストリークを計算・更新する
    昨日から連続していれば +1、そうでなければ 1 にリセット
    
    Args:
        hkey: ハッシュ化されたユーザーID
        ac_date: AC日付（ISO形式: YYYY-MM-DD）
        streak_state: ストリーク情報辞書
    
    Returns:
        新しいストリーク日数
    """
    prev_ac_date: str = streak_state.get(f"{hkey}_last_ac_date", "")
    
    # 前回のAC日が「昨日」かどうかを判定
    yesterday_str = (
        datetime.datetime.fromisoformat(ac_date)
        - datetime.timedelta(days=1)
    ).date().isoformat()
    
    if prev_ac_date == yesterday_str:
        # 昨日から連続 → ストリーク継続
        prev_streak = streak_state.get(f"{hkey}_streak", 0)
        new_streak = prev_streak + 1
    else:
        # 昨日ではない → ストリークリセット
        new_streak = 1
    
    return new_streak


# ──────────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """コマンドラインオプションをパースする"""
    parser = argparse.ArgumentParser(
        description="AtCoder AC 通知スクリプト"
    )
    parser.add_argument(
        "--channel_id",
        type=str,
        default="",
        help="通知先の Slack チャンネルID（指定時は Bot API を使用）",
    )
    parser.add_argument(
        "--user_id",
        type=str,
        default="",
        help="対象の AtCoder ユーザーID（指定時はこのユーザーのみをチェック）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    channel_id = args.channel_id if args.channel_id else None
    user_id = args.user_id if args.user_id else None
    
    members = load_members()
    state = load_state()
    streak_state = load_streak()

    # user_id が指定されている場合は、該当ユーザーのみをフィルタリング
    if user_id:
        members = [m for m in members if m["atcoder_id"] == user_id]
        if not members:
            print(f"[ERROR] ユーザー {user_id} が見つかりません。")
            return

    today_str = datetime.datetime.now(JST).date().isoformat()

    # 初回実行時に過去提出を大量通知しないよう、現在時刻の15分前を下限にする
    default_from_second = int(time.time()) - 15 * 60
    
    # この実行で新しいAC提出があったかどうかを追跡
    has_new_submissions = False

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

            # 前回のAC日を取得（新しい日付かどうかを判定するため）
            prev_ac_date: str = streak_state.get(f"{hkey}_last_ac_date", "")
            is_first_ac_on_this_date = (prev_ac_date != sub_date)

            # 新規AC検出 → ストリークを計算・更新
            new_streak = update_streak_for_date(hkey, sub_date, streak_state)
            streak_state[f"{hkey}_streak"] = new_streak
            streak_state[f"{hkey}_last_ac_date"] = sub_date

            # その日初めてのACの場合、streak情報を含めて通知
            streak_info = new_streak if is_first_ac_on_this_date else None
            message = build_slack_message(display_name, sub, streak_info)
            post_to_slack(message, channel_id=channel_id)
            print(f"[INFO] {atcoder_id}: AC on {sub_date}, streak={new_streak}")
            has_new_submissions = True
            
            new_last_id = max(new_last_id, sub["id"])
            new_last_epoch = max(new_last_epoch, sub["epoch_second"])

        # 状態を更新
        state[hkey] = new_last_id
        state[f"{hkey}_epoch"] = new_last_epoch

        time.sleep(REQUEST_INTERVAL_SEC)

    # channel_id が指定されていない場合（スケジュール実行）のみ状態ファイルを更新
    if not channel_id:
        save_state(state)
        save_streak(streak_state)
        print("[INFO] 状態ファイルを更新しました。")
    else:
        print("[INFO] 手動実行のため、状態ファイルは更新されません。")
    
    # channel_id が指定されている場合（手動実行）かつ 提出がなかった場合は Slack で通知
    if channel_id and not has_new_submissions:
        message = "there were no new AC submissions"
        post_to_slack(message, channel_id=channel_id)
        print("[INFO] 新しい提出がなかったことを通知しました。")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AtCoder Problems API を使用してstreak日数を確認・集計するスクリプト
"""

import argparse
import os
import sys
import time
import yaml
from datetime import datetime, timedelta
from pathlib import Path

# 親ディレクトリの utils パッケージをインポート
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import hash_id, save_streak, post_to_slack, fetch_submissions, load_members, load_streak
from utils.constants import JST


def parse_args() -> argparse.Namespace:
    """コマンドラインオプションをパースする"""
    parser = argparse.ArgumentParser(
        description="AtCoder Streak カウンタースクリプト"
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
        help="対象の AtCoder ユーザーID（指定時はこのユーザーのみを集計）",
    )
    return parser.parse_args()


def extract_ac_dates(submissions):
    """提出履歴から AC 日付を抽出（日付ごとに1回のみ、JST で統一）"""
    ac_dates = set()
    for submission in submissions:
        if submission.get('result') == 'AC':
            # Unix timestamp を JST の Date に変換（環境依存を排除）
            timestamp = submission.get('epoch_second', 0)
            ac_date = datetime.fromtimestamp(timestamp, tz=JST).date()
            ac_dates.add(ac_date)
    return sorted(ac_dates, reverse=True)  # 最新の日付が最初


def calculate_streak(ac_dates, today):
    """AC日付リストからstreak日数を計算"""
    if not ac_dates:
        return 0, None

    # 最新のAC日
    latest_ac_date = ac_dates[0]

    # 昨日または今日にACがないとストリークは0
    yesterday = today - timedelta(days=1)
    if latest_ac_date != today and latest_ac_date != yesterday:
        return 0, latest_ac_date

    # ストリークを数える
    streak = 1
    for i in range(len(ac_dates) - 1):
        current_date = ac_dates[i]
        next_date = ac_dates[i + 1]
        expected_next = current_date - timedelta(days=1)
        if next_date == expected_next:
            streak += 1
        else:
            break

    return streak, latest_ac_date


def generate_ranking_table(members_dict, streak_data, today):
    """ランキング情報をテーブル形式で生成（コンソール用）"""
    # ストリークデータをランキング用に整形
    ranking_data = []
    yesterday = today - timedelta(days=1)

    for atcoder_id in members_dict.keys():
        display_name = members_dict[atcoder_id]
        streak = streak_data[atcoder_id]['streak']
        last_ac_date = streak_data[atcoder_id]['last_ac_date']
        
        if last_ac_date:
            is_active = last_ac_date == today or last_ac_date == yesterday
            status = '✅' if is_active else '🔺'
        else:
            is_active = False
            status = '❌'
        
        ranking_data.append({
            'atcoder_id': atcoder_id,
            'display_name': display_name,
            'streak': streak,
            'last_ac_date': last_ac_date,
            'status': status,
            'is_active': is_active,
        })
    
    # ストリーク日数で降順にソート
    ranking_data.sort(key=lambda x: x['streak'], reverse=True)
    
    # テーブル行を生成
    lines = []
    lines.append("=" * 75)
    lines.append(f"{'Rank':<6} | {'Status':<4} | {'AtCoder ID':<16} | {'Streak':<8} | {'Last AC':<12}")
    lines.append("-" * 75)
    
    total_streak = 0
    active_users = 0
    
    for rank, data in enumerate(ranking_data, 1):
        if data['is_active']:
            active_users += 1
            total_streak += data['streak']
        
        last_ac_str = data['last_ac_date'].strftime('%Y-%m-%d') if data['last_ac_date'] else 'N/A'
        rank_str = f"#{rank}"
        lines.append(f"{rank_str:<6} | {data['status']}     | {data['atcoder_id']:<16} | {data['streak']:<8} | {last_ac_str:<12}")
    
    lines.append("=" * 75)
    lines.append(f"🔥 Active Users: {active_users}")
    
    return "\n".join(lines), active_users, total_streak


def display_streak_info(members_dict, streak_data, today):
    """ストリーク情報をランキング形式で表示"""
    table, _, _ = generate_ranking_table(members_dict, streak_data, today)
    print(f"\n{table}\n")


def build_slack_blocks(members_dict, streak_data, today):
    """Block Kitを使ったSlack用リッチメッセージを生成（表形式）"""
    ranking_data = []
    yesterday = today - timedelta(days=1)

    for atcoder_id in members_dict.keys():
        display_name = members_dict[atcoder_id]
        streak = streak_data[atcoder_id]['streak']
        last_ac_date = streak_data[atcoder_id]['last_ac_date']
        
        if last_ac_date:
            is_active = last_ac_date == today or last_ac_date == yesterday
            status = '✅' if is_active else '🔺'
        else:
            is_active = False
            status = '❌'
        
        ranking_data.append({
            'atcoder_id': atcoder_id,
            'display_name': display_name,
            'streak': streak,
            'last_ac_date': last_ac_date,
            'status': status,
            'is_active': is_active,
        })
    
    # ストリーク日数で降順にソート
    ranking_data.sort(key=lambda x: x['streak'], reverse=True)
    
    blocks = []
    
    # ヘッダー
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": ":accepted: AtCoder Streak Ranking"
        }
    })
    
    # 日付
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"_as of {today}_"
            }
        ]
    })
    
    # テーブルヘッダー（固定幅フォント）
    header_text = "```\nRank        Status    AtCoder ID           Streak    Last AC\n" + "─" * 75 + "\n"
    
    active_users = 0
    total_streak = 0
    
    # データ行
    for rank, data in enumerate(ranking_data, 1):
        if data['is_active']:
            active_users += 1
            total_streak += data['streak']
        
        last_ac_str = data['last_ac_date'].strftime('%Y-%m-%d') if data['last_ac_date'] else 'N/A'
        
        # ランク（メダル表示）
        # if rank == 1:
        #     rank_text = "🥇 #1"
        # elif rank == 2:
        #     rank_text = "🥈 #2"
        # elif rank == 3:
        #     rank_text = "🥉 #3"
        # else:
        #     rank_text = f"#{rank}"
        rank_text = f"#{rank}"
        
        # 固定幅で整形（Slack の monospace フォントで表示）
        header_text += f"{rank_text:<12}{data['status']:<10}{data['atcoder_id']:<21}{data['streak']:<10}{last_ac_str}\n"
    
    header_text += "```"
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": header_text
        }
    })
    
    # 区切り線
    blocks.append({"type": "divider"})
    
    # フッター
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"🔥 Active Users: {active_users}"
            }
        ]
    })
    
    return blocks


def notify_slack(streak_data, members_dict, today, channel_id: str | None = None):
    """streak情報をSlackでランキング形式で通知"""
    blocks = build_slack_blocks(members_dict, streak_data, today)
    post_to_slack(blocks=blocks, channel_id=channel_id)


def save_streak_data(streak_data, is_partial_update: bool = False):
    """streak情報をdata/streak.jsonに保存（utils.py の save_streak() を使用）"""
    # utils の save_streak() 用に形式を変換
    import json
    streak_dict = {}
    
    # 部分更新の場合は既存データを読み込む
    if is_partial_update:
        existing_streak = load_streak()
        streak_dict.update(existing_streak)
    
    # 新しいデータをマージ
    for atcoder_id, data in streak_data.items():
        hkey = hash_id(atcoder_id)
        streak_dict[f"{hkey}_streak"] = data['streak']
        last_ac_date = data['last_ac_date']
        if last_ac_date:
            streak_dict[f"{hkey}_last_ac_date"] = last_ac_date.isoformat()
    
    save_streak(streak_dict)
    print("✓ 保存完了: data/streak.json")


def main():
    args = parse_args()
    channel_id = args.channel_id if args.channel_id else None
    user_id = args.user_id if args.user_id else None
    
    # メンバー情報を読み込む（list[dict] から dict に変換）
    members_list = load_members()
    if not members_list:
        return
    members_dict = {m['atcoder_id']: m['display_name'] for m in members_list}
    
    # user_id が指定されている場合は、該当ユーザーのみをフィルタリング
    if user_id:
        if user_id not in members_dict:
            print(f"[ERROR] ユーザー {user_id} が見つかりません。")
            return
        members_dict = {user_id: members_dict[user_id]}

    today = datetime.now(JST).date()
    streak_data = {}
    
    # 直近400件の提出を取得するため、過去3ヶ月を from_second に設定
    # APIは古い順に最大500件を返すため、このパラメータで最新データを確保
    from_second = int(time.time()) - (90 * 24 * 60 * 60)  # 過去3ヶ月

    print(f"=== AtCoder Streak Counter (as of {today}) ===\n")
    print("提出履歴を取得中...")

    # 各メンバーのストリークを計算
    for atcoder_id, display_name in members_dict.items():
        print(f"  {display_name} ({atcoder_id})...", end='', flush=True)
        
        # 過去3ヶ月以降の提出を取得
        submissions = fetch_submissions(atcoder_id, from_second=from_second)
        
        # 直近400件のみを使用
        if len(submissions) > 400:
            submissions = submissions[-400:]
        
        ac_dates = extract_ac_dates(submissions)
        streak, last_ac_date = calculate_streak(ac_dates, today)

        streak_data[atcoder_id] = {
            'streak': streak,
            'last_ac_date': last_ac_date
        }
        print(" OK")

    # 結果を表示
    display_streak_info(members_dict, streak_data, today)

    # streak.json に保存（user_id が指定されている場合は部分更新）
    print("\nデータを保存中...")
    save_streak_data(streak_data, is_partial_update=(user_id is not None))

    # Slack に通知
    print("Slack通知を送信中...")
    notify_slack(streak_data, members_dict, today, channel_id=channel_id)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
AtCoder Problems API を使用してstreak日数を確認・集計するスクリプト
"""

import os
import sys
import time
import yaml
from datetime import datetime, timedelta
from pathlib import Path

# 親ディレクトリの utils パッケージをインポート
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import hash_id, save_streak, post_to_slack, fetch_submissions, load_members


def extract_ac_dates(submissions):
    """提出履歴から AC 日付を抽出（日付ごとに1回のみ）"""
    ac_dates = set()
    for submission in submissions:
        if submission.get('result') == 'AC':
            # Unix timestamp をDateに変換
            timestamp = submission.get('epoch_second', 0)
            ac_date = datetime.fromtimestamp(timestamp).date()
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


def display_streak_info(members_dict, streak_data, today):
    """ストリーク情報を表示"""
    print(f"\n{'AtCoder ID':<20} | {'Display Name':<15} | {'Streak':<8} | {'Last AC':<12} | {'Status':<8}")
    print("-" * 75)

    total_streak = 0
    active_users = 0

    for atcoder_id in sorted(members_dict.keys()):
        display_name = members_dict[atcoder_id]
        streak = streak_data[atcoder_id]['streak']
        last_ac_date = streak_data[atcoder_id]['last_ac_date']

        if last_ac_date:
            yesterday = today - timedelta(days=1)
            is_active = last_ac_date == today or last_ac_date == yesterday
            status = '🔥 Active' if is_active else '⚠️  Broken'
            if is_active:
                active_users += 1
                total_streak += streak
        else:
            status = '❌ None'
            last_ac_date = 'N/A'

        last_ac_str = last_ac_date.strftime('%Y-%m-%d') if isinstance(last_ac_date, datetime) else str(last_ac_date)
        print(f"{atcoder_id:<20} | {display_name:<15} | {streak:<8} | {last_ac_str:<12} | {status:<8}")

    print("-" * 75)
    print(f"{'Total':<20} | {'':<15} | {total_streak:<8} | {'Active':<12} | {active_users:<8}")
    print()


def notify_slack(streak_data, members_dict, today):
    """streak情報をSlackで通知"""
    # ストリーク情報をまとめたメッセージを作成
    message_lines = [":accepted: *AtCoder Streak Report*"]
    message_lines.append(f"_as of {today}_\n")

    total_streak = 0
    active_users = 0
    yesterday = today - timedelta(days=1)

    for atcoder_id in sorted(members_dict.keys()):
        display_name = members_dict[atcoder_id]
        streak = streak_data[atcoder_id]['streak']
        last_ac_date = streak_data[atcoder_id]['last_ac_date']

        if last_ac_date:
            is_active = last_ac_date == today or last_ac_date == yesterday
            if is_active:
                status = "🔥"
                active_users += 1
                total_streak += streak
            else:
                status = "⚠️"
        else:
            status = "❌"

        last_ac_str = last_ac_date.strftime('%Y-%m-%d') if last_ac_date else "N/A"
        # message_lines.append(f"{status} *{display_name}* ({atcoder_id}): {streak} days | Last AC: {last_ac_str}")
        message_lines.append(f"{status} *{atcoder_id}* : {streak} days | Last AC: {last_ac_str}")

    # message_lines.append("")
    # message_lines.append(f"*Total Active Streak:* {total_streak} days ({active_users} active)")

    message = "\n".join(message_lines)
    post_to_slack(message)


def save_streak_data(streak_data):
    """streak情報をdata/streak.jsonに保存（utils.py の save_streak() を使用）"""
    # utils の save_streak() 用に形式を変換
    import json
    streak_dict = {}
    for atcoder_id, data in streak_data.items():
        hkey = hash_id(atcoder_id)
        streak_dict[f"{hkey}_streak"] = data['streak']
        last_ac_date = data['last_ac_date']
        if last_ac_date:
            streak_dict[f"{hkey}_last_ac_date"] = last_ac_date.isoformat()
    
    save_streak(streak_dict)
    print("✓ 保存完了: data/streak.json")


def main():
    # メンバー情報を読み込む（list[dict] から dict に変換）
    members_list = load_members()
    if not members_list:
        return
    members_dict = {m['atcoder_id']: m['display_name'] for m in members_list}

    today = datetime.now().date()
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

    # streak.json に保存
    print("\nデータを保存中...")
    save_streak_data(streak_data)

    # Slack に通知
    print("Slack通知を送信中...")
    notify_slack(streak_data, members_dict, today)


if __name__ == '__main__':
    main()

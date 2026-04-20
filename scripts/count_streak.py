#!/usr/bin/env python3
"""
AtCoder Problems API を使用してstreak日数を確認・集計するスクリプト
"""

import json
import os
import yaml
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


def load_members():
    """メンバー情報を環境変数またはファイルから読み込む"""
    # 環境変数 MEMBERS_YAML から取得（優先度最高）
    members_yaml = os.environ.get('MEMBERS_YAML')
    if members_yaml:
        try:
            data = yaml.safe_load(members_yaml)
            if data and 'members' in data:
                return {m['atcoder_id']: m['display_name'] for m in data['members']}
        except Exception as e:
            print(f"Warning: MEMBERS_YAML の解析に失敗: {e}")

    # 環境変数 MEMBERS_JSON から取得（フォールバック）
    members_json = os.environ.get('MEMBERS_JSON')
    if members_json:
        try:
            data = json.loads(members_json)
            return {m['atcoder_id']: m['display_name'] for m in data}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: MEMBERS_JSON の解析に失敗: {e}")

    # ファイルから取得（フォールバック）
    members_file = Path(__file__).parent.parent / 'data' / 'members.yml'
    if members_file.exists():
        try:
            with open(members_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and 'members' in data:
                    return {m['atcoder_id']: m['display_name'] for m in data['members']}
        except Exception as e:
            print(f"Warning: members.yml の読み込みに失敗: {e}")

    print("Error: メンバー情報が見つかりません（MEMBERS_YAML 環境変数、MEMBERS_JSON、または data/members.yml を設定してください）")
    return {}


def get_user_submissions(atcoder_id):
    """AtCoder Problems API からユーザーの提出履歴を取得"""
    url = f"https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?user={atcoder_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: {atcoder_id} の提出履歴取得に失敗: {e}")
        return []


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


def main():
    # メンバー情報を読み込む
    members_dict = load_members()
    if not members_dict:
        return

    today = datetime.now().date()
    streak_data = {}

    print(f"=== AtCoder Streak Counter (as of {today}) ===\n")
    print("提出履歴を取得中...")

    # 各メンバーのストリークを計算
    for atcoder_id, display_name in members_dict.items():
        print(f"  {display_name} ({atcoder_id})...", end='', flush=True)
        
        submissions = get_user_submissions(atcoder_id)
        ac_dates = extract_ac_dates(submissions)
        streak, last_ac_date = calculate_streak(ac_dates, today)

        streak_data[atcoder_id] = {
            'streak': streak,
            'last_ac_date': last_ac_date
        }
        print(" OK")

    # 結果を表示
    display_streak_info(members_dict, streak_data, today)


if __name__ == '__main__':
    main()

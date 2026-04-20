#!/usr/bin/env python3
"""
peach2587の提出履歴をデバッグするスクリプト
"""

import requests
from datetime import datetime, timedelta

atcoder_id = "peach2587"
url = f"https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?user={atcoder_id}"

print(f"APIリクエスト: {url}\n")

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    submissions = response.json()
    
    print(f"取得した提出件数: {len(submissions)}\n")
    
    # AC提出のみを抽出
    ac_submissions = [s for s in submissions if s.get('result') == 'AC']
    print(f"AC提出数: {len(ac_submissions)}\n")
    
    # AC日付を抽出
    ac_dates = set()
    for submission in ac_submissions:
        timestamp = submission.get('epoch_second', 0)
        if timestamp:
            ac_date = datetime.fromtimestamp(timestamp).date()
            ac_dates.add(ac_date)
    
    ac_dates_sorted = sorted(ac_dates, reverse=True)
    
    print(f"AC日数（ユニーク）: {len(ac_dates_sorted)}\n")
    print("最新のAC日付（10件）:")
    for i, date in enumerate(ac_dates_sorted[:10]):
        print(f"  {i+1}. {date}")
    
    # Streak計算
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    if not ac_dates_sorted:
        print(f"\n❌ AC提出がありません")
    else:
        latest_ac_date = ac_dates_sorted[0]
        print(f"\n最新AC日: {latest_ac_date}")
        print(f"今日の日付: {today}")
        print(f"昨日の日付: {yesterday}")
        
        if latest_ac_date == today or latest_ac_date == yesterday:
            # ストリーク計算
            streak = 1
            for i in range(len(ac_dates_sorted) - 1):
                current_date = ac_dates_sorted[i]
                next_date = ac_dates_sorted[i + 1]
                expected_next = current_date - timedelta(days=1)
                if next_date == expected_next:
                    streak += 1
                else:
                    break
            print(f"✅ ストリーク: {streak} days")
        else:
            print(f"❌ ストリーク: 0 days（昨日もしくは今日にACがない）")
    
    # 最新の提出内容を確認
    if ac_submissions:
        print(f"\n最新AC提出3件の詳細:")
        for i, sub in enumerate(ac_submissions[-3:][::-1]):
            sub_date = datetime.fromtimestamp(sub.get('epoch_second', 0)).date()
            print(f"  {i+1}. {sub_date} - {sub.get('contest_id')} / {sub.get('problem_id')}")
    
except requests.RequestException as e:
    print(f"❌ APIエラー: {e}")
except Exception as e:
    print(f"❌ エラー: {e}")

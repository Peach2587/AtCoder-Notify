#!/usr/bin/env python3
"""
check_ac.py のデバッグスクリプト
peach2587 のデータを詳細に確認
"""

import sys
from pathlib import Path
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import hash_id, fetch_submissions, load_state, load_streak

JST = ZoneInfo("Asia/Tokyo")

atcoder_id = "peach2587"
hkey = hash_id(atcoder_id)

print(f"=== デバッグ: {atcoder_id} ===\n")

# 保存されたstate を確認
state = load_state()
streak_state = load_streak()

print("[1] 保存されたstate:")
print(f"  last_id: {state.get(hkey, 'なし')}")
print(f"  last_epoch: {state.get(f'{hkey}_epoch', 'なし')}")

if state.get(f'{hkey}_epoch'):
    last_epoch_date = datetime.fromtimestamp(state.get(f'{hkey}_epoch')).strftime('%Y-%m-%d %H:%M:%S')
    print(f"  last_epoch_date: {last_epoch_date}")

print(f"\n[2] 保存されたstreak状態:")
print(f"  streak: {streak_state.get(f'{hkey}_streak', 'なし')}")
print(f"  last_ac_date: {streak_state.get(f'{hkey}_last_ac_date', 'なし')}")

# from_second の値を決定するロジック
default_from_second = int(time.time()) - 15 * 60
from_second = state.get(f'{hkey}_epoch', default_from_second)

print(f"\n[3] APIリクエストに使用する値:")
print(f"  from_second: {from_second}")
print(f"  from_second_date: {datetime.fromtimestamp(from_second).strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  現在時刻 - 15分: {datetime.fromtimestamp(default_from_second).strftime('%Y-%m-%d %H:%M:%S')}")

# APIから全提出を取得（from_second=0）
print(f"\n[4] API呼び出し（全履歴）...")
all_submissions = fetch_submissions(atcoder_id, from_second=0)
print(f"  取得件数: {len(all_submissions)}")

# AC提出を抽出
ac_submissions_all = [s for s in all_submissions if s.get('result') == 'AC']
print(f"  AC提出数: {len(ac_submissions_all)}")

if ac_submissions_all:
    # 最新のAC
    latest_ac = max(ac_submissions_all, key=lambda s: s['epoch_second'])
    latest_ac_date = datetime.fromtimestamp(latest_ac['epoch_second'], tz=JST).date()
    latest_ac_time = datetime.fromtimestamp(latest_ac['epoch_second'], tz=JST)
    print(f"  最新AC日時: {latest_ac_time.strftime('%Y-%m-%d %H:%M:%S (JST)')}")
    print(f"  最新AC日: {latest_ac_date}")
    print(f"  最新AC提出ID: {latest_ac['id']}")
    print(f"  最新AC問題: {latest_ac['contest_id']} / {latest_ac['problem_id']}")

# from_second 以降の提出を取得
print(f"\n[5] API呼び出し（from_second={from_second} 以降）...")
submissions = fetch_submissions(atcoder_id, from_second=from_second)
print(f"  取得件数: {len(submissions)}")

ac_submissions = sorted(
    [s for s in submissions if s.get('result') == 'AC'],
    key=lambda s: s['id'],
)
print(f"  AC提出数: {len(ac_submissions)}")

if ac_submissions:
    # from_second以降の最新AC
    latest_recent = max(ac_submissions, key=lambda s: s['epoch_second'])
    latest_recent_date = datetime.fromtimestamp(latest_recent['epoch_second'], tz=JST).date()
    latest_recent_time = datetime.fromtimestamp(latest_recent['epoch_second'], tz=JST)
    print(f"  最新AC日時: {latest_recent_time.strftime('%Y-%m-%d %H:%M:%S (JST)')}")
    print(f"  最新AC日: {latest_recent_date}")
else:
    print(f"  ⚠️ from_second以降にAC提出がありません")

# 差分確認
print(f"\n[6] 解析:")
if ac_submissions_all and ac_submissions:
    print(f"  全AC履歴の最新: {latest_ac_date}")
    print(f"  from_second以降の最新: {latest_recent_date}")
    if latest_ac_date != latest_recent_date:
        print(f"  ⚠️ 異なる日付です（最後のstateで from_second が固定されている可能性）")
elif ac_submissions_all and not ac_submissions:
    print(f"  全AC履歴の最新: {latest_ac_date}")
    print(f"  ❌ from_second以降のAC提出がないため、count_streak.pyとの差が生じる")

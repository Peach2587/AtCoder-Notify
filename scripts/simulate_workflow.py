#!/usr/bin/env python3
"""
次のcheck_ac.py実行時に何が通知されるかをシミュレート
"""

import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import (
    hash_id, load_state, load_streak, fetch_submissions, load_members, JST
)

def main():
    print("=" * 80)
    print("次のワークフロー実行時の通知シミュレーション")
    print("=" * 80)
    
    members = load_members()
    state = load_state()
    streak_state = load_streak()
    
    today_str = datetime.now(JST).date().isoformat()
    default_from_second = int(time.time()) - 15 * 60
    
    print(f"\n📅 実行日時: {today_str}")
    print(f"⏰ from_second: {default_from_second} ({datetime.fromtimestamp(default_from_second).strftime('%Y-%m-%d %H:%M:%S')})\n")
    
    total_new_ac = 0
    first_ac_today_count = 0
    
    for member in members:
        atcoder_id = member["atcoder_id"]
        display_name = member["display_name"]
        hkey = hash_id(atcoder_id)
        
        last_id = state.get(hkey, 0)
        from_second = state.get(f"{hkey}_epoch", default_from_second)
        last_ac_date = streak_state.get(f"{hkey}_last_ac_date", "")
        
        print(f"👤 {display_name}")
        
        # API から提出を取得
        submissions = fetch_submissions(atcoder_id, from_second)
        ac_submissions = sorted(
            [s for s in submissions if s.get("result") == "AC"],
            key=lambda s: s["id"],
        )
        
        # 新規AC
        new_ac_submissions = [s for s in ac_submissions if s["id"] > last_id]
        print(f"   新規AC数: {len(new_ac_submissions)} 件")
        
        if new_ac_submissions:
            total_new_ac += len(new_ac_submissions)
            
            # その日初めてのACをチェック
            for sub in new_ac_submissions:
                sub_date = datetime.fromtimestamp(
                    sub["epoch_second"], tz=JST
                ).date().isoformat()
                
                prev_ac_date = streak_state.get(f"{hkey}_last_ac_date", "")
                is_first_ac_on_this_date = (prev_ac_date != sub_date)
                
                if is_first_ac_on_this_date:
                    # ストリークを計算
                    yesterday_str = (
                        datetime.fromisoformat(sub_date)
                        - __import__('datetime').timedelta(days=1)
                    ).date().isoformat()
                    
                    prev_streak = streak_state.get(f"{hkey}_streak", 0)
                    if prev_ac_date == yesterday_str:
                        new_streak = prev_streak + 1
                    else:
                        new_streak = 1
                    
                    first_ac_today_count += 1
                    status = "🔥 (その日初AC - streak通知付き)"
                    print(f"   ✓ ID {sub['id']}: {sub['contest_id']}/{sub['problem_id']} ({sub_date}) - {status}")
                    print(f"      → Slack通知: Current Streak: {new_streak} days")
                else:
                    status = "✓ (通常通知)"
                    print(f"   ✓ ID {sub['id']}: {sub['contest_id']}/{sub['problem_id']} ({sub_date}) - {status}")
        else:
            print(f"   → 新規提出なし（通知なし）")
        
        print()
        time.sleep(1.0)
    
    print("=" * 80)
    print(f"📊 通知サマリー")
    print("=" * 80)
    print(f"総新規AC数: {total_new_ac} 件")
    print(f"その日初AC（streak通知付き）: {first_ac_today_count} 件")
    print(f"通常通知: {total_new_ac - first_ac_today_count} 件")
    print()
    
    if total_new_ac == 0:
        print("⏸️  次のワークフロー実行では通知が発生しません（新規提出なし）")
    elif total_new_ac > 50:
        print(f"⚠️  大量の新規AC ({total_new_ac} 件) が通知される可能性があります")
    else:
        print(f"✅ 正常：{total_new_ac} 件の新規AC通知が予期されます")

if __name__ == "__main__":
    main()

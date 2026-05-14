#!/usr/bin/env python3
"""
大量通知の原因をデバッグするスクリプト
- 各メンバーの前回の提出ID と from_second を確認
- API から返ってくる提出数をカウント
- 新規通知対象の提出がいくつあるか確認
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
    print("大量通知デバッグ分析")
    print("=" * 80)
    
    members = load_members()
    if not members:
        print("[ERROR] メンバー情報が見つかりません")
        return
    
    state = load_state()
    streak_state = load_streak()
    
    today_str = datetime.now(JST).date().isoformat()
    default_from_second = int(time.time()) - 15 * 60
    
    print(f"\n📅 実行日時: {today_str}")
    print(f"⏰ デフォルト from_second: {default_from_second} ({datetime.fromtimestamp(default_from_second).strftime('%Y-%m-%d %H:%M:%S')})")
    print()
    
    for member in members:
        atcoder_id = member["atcoder_id"]
        display_name = member["display_name"]
        hkey = hash_id(atcoder_id)
        
        last_id = state.get(hkey, 0)
        from_second = state.get(f"{hkey}_epoch", default_from_second)
        last_ac_date = streak_state.get(f"{hkey}_last_ac_date", "")
        
        print(f"👤 {display_name} ({atcoder_id})")
        print(f"   ハッシュID: {hkey}")
        print(f"   前回の提出ID: {last_id}")
        print(f"   from_second: {from_second} ({datetime.fromtimestamp(from_second).strftime('%Y-%m-%d %H:%M:%S')})")
        print(f"   最後のAC日: {last_ac_date}")
        
        # API から提出を取得
        print(f"   → API から提出を取得中...", end="", flush=True)
        submissions = fetch_submissions(atcoder_id, from_second)
        print(f" (全体: {len(submissions)} 件)")
        
        # AC 提出のみ抽出
        ac_submissions = [s for s in submissions if s.get("result") == "AC"]
        print(f"   → AC 提出のみ: {len(ac_submissions)} 件")
        
        if ac_submissions:
            ac_ids = [s["id"] for s in ac_submissions]
            print(f"   → AC提出ID範囲: {min(ac_ids)} ～ {max(ac_ids)}")
        
        # 新規通知対象
        new_ac_count = sum(1 for s in ac_submissions if s["id"] > last_id)
        print(f"   ⚠️  新規通知対象: {new_ac_count} 件（ID > {last_id}）")
        
        if new_ac_count > 0:
            new_ac_ids = [s["id"] for s in ac_submissions if s["id"] > last_id]
            print(f"      新規提出ID: {min(new_ac_ids)} ～ {max(new_ac_ids)}")
            
            # 新規提出の詳細
            print(f"      詳細:")
            for s in sorted([s for s in ac_submissions if s["id"] > last_id], key=lambda x: x["id"]):
                sub_date = datetime.fromtimestamp(s["epoch_second"], tz=JST).date().isoformat()
                print(f"        - ID {s['id']}: {s['contest_id']}/{s['problem_id']} (AC日: {sub_date})")
        
        print()
        time.sleep(1.0)  # API レート制限対策
    
    print("=" * 80)
    print("分析完了")
    print("=" * 80)

if __name__ == "__main__":
    main()

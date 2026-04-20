"""
API呼び出しユーティリティ
"""

import sys

import requests

from .constants import SUBMISSIONS_API


def fetch_submissions(atcoder_id: str, from_second: int) -> list[dict]:
    """
    AtCoder Problems API からユーザーの提出履歴を取得する。
    from_second 以降（Unix 秒）の提出のみ返す。
    
    Args:
        atcoder_id: AtCoder ユーザーID
        from_second: Unix タイムスタンプ（この秒数以降の提出を取得）
        
    Returns:
        提出情報の辞書リスト。API呼び出しに失敗した場合は空リスト。
    """
    params = {"user": atcoder_id, "from_second": from_second}
    try:
        response = requests.get(SUBMISSIONS_API, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] API request failed for {atcoder_id}: {e}", file=sys.stderr)
        return []

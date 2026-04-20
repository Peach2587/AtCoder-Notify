"""
ハッシュ関連ユーティリティ
"""

import hashlib


def hash_id(atcoder_id: str) -> str:
    """
    AtCoder ID を SHA-256 でハッシュ化してキーとして使う。
    JSONに生IDを残さないため、ハッシュ化した値を使用。
    
    Args:
        atcoder_id: AtCoder ユーザーID
        
    Returns:
        SHA-256 ハッシュの先頭16文字
    """
    return hashlib.sha256(atcoder_id.encode()).hexdigest()[:16]

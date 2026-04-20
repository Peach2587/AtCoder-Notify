"""
ファイル操作ユーティリティ
"""

import json

from .constants import STATE_FILE, STREAK_FILE


def load_state() -> dict:
    """
    data/last_submission_ids.json を読み込む。
    ファイルがなければ空dictを返す。
    
    Returns:
        提出状態を含む辞書
    """
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    """
    data/last_submission_ids.json に状態を保存する。
    
    Args:
        state: 保存する提出状態の辞書
    """
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_streak() -> dict:
    """
    data/streak.json を読み込む。
    ファイルがなければ空dictを返す。
    
    Returns:
        ストリーク情報を含む辞書
    """
    if STREAK_FILE.exists():
        with open(STREAK_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_streak(streak_state: dict) -> None:
    """
    data/streak.json にストリーク情報を保存する。
    
    Args:
        streak_state: 保存するストリーク情報の辞書
    """
    with open(STREAK_FILE, "w", encoding="utf-8") as f:
        json.dump(streak_state, f, ensure_ascii=False, indent=2)

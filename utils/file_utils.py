"""
ファイル操作ユーティリティ
"""

import json
import os
import yaml

from .constants import STATE_FILE, STREAK_FILE, REPO_ROOT


def load_members() -> list[dict]:
    """
    メンバー情報を環境変数またはファイルから読み込む（優先度順）
    
    1. MEMBERS_YAML 環境変数
    2. MEMBERS_JSON 環境変数
    3. data/members.yml ファイル
    
    Returns:
        メンバーのリスト: [{'atcoder_id': '...', 'display_name': '...'}, ...]
    """
    # 環境変数 MEMBERS_YAML から取得（優先度最高）
    members_yaml = os.environ.get('MEMBERS_YAML')
    if members_yaml:
        try:
            data = yaml.safe_load(members_yaml)
            if data and 'members' in data:
                return data['members']
        except Exception as e:
            print(f"[WARN] MEMBERS_YAML の解析に失敗: {e}")

    # 環境変数 MEMBERS_JSON から取得（フォールバック）
    members_json = os.environ.get('MEMBERS_JSON')
    if members_json:
        try:
            data = json.loads(members_json)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[WARN] MEMBERS_JSON の解析に失敗: {e}")

    # ファイルから取得（フォールバック）
    members_file = REPO_ROOT / "data" / "members.yml"
    if members_file.exists():
        try:
            with open(members_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and 'members' in data:
                    return data.get("members", [])
        except Exception as e:
            print(f"[WARN] {members_file} の読み込みに失敗: {e}")

    print("[ERROR] メンバー情報が見つかりません（MEMBERS_YAML 環境変数、MEMBERS_JSON、または data/members.yml を設定してください）")
    return []


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

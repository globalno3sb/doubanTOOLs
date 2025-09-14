# -*- coding: utf-8 -*-
import json
import os

def load_token_json(path: str | None = None) -> dict:
    """从 token.json 读取 {"access_token": "..."}（可选）"""
    path = path or os.path.join(os.path.dirname(__file__), "token.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def get_trakt_credentials(cli_client_id: str | None, cli_token: str | None) -> tuple[str, str | None]:
    """
    获取 Trakt 凭据优先级：
      1) 命令行参数 --trakt-client-id / --trakt-token
      2) 环境变量 TRAKT_CLIENT_ID / TRAKT_ACCESS_TOKEN
      3) token.json 里的 access_token（仅 token；client_id 仍需 1/2 提供）
    返回: (client_id, access_token_or_None)
    """
    env_client_id = os.getenv("TRAKT_CLIENT_ID")
    env_token = os.getenv("TRAKT_ACCESS_TOKEN")

    client_id = cli_client_id or env_client_id
    token = cli_token or env_token

    if not token:
        token = load_token_json().get("access_token")

    return client_id, token
# -*- coding: utf-8 -*-
import argparse
from config import get_trakt_credentials
from importer import migrate_from_csv

def main():
    p = argparse.ArgumentParser(description="根据 CSV（经人工校对过的匹配结果）同步到 Trakt")
    p.add_argument("--csv", required=True, help="CSV 文件路径（title,date,datetime,type,season,slug,matched_title,matched_year,found,douban_link）")
    p.add_argument("-t", "--type", choices=["watched","watchlist"], required=True,
                   help="watched => /sync/history；watchlist => /sync/watchlist")
    p.add_argument("--trakt-client-id", default=None, help="Trakt Client ID（未提供则读环境变量 TRAKT_CLIENT_ID）")
    p.add_argument("--trakt-token", default=None, help="Trakt Access Token（未提供则读环境变量 TRAKT_ACCESS_TOKEN 或 token.json）")
    p.add_argument("--dry-run", action="store_true", help="只生成 payload，不写入 Trakt")
    args = p.parse_args()

    client_id, token = get_trakt_credentials(args.trakt_client_id, args.trakt_token)
    if not client_id:
        raise SystemExit("缺少 Trakt Client ID。请使用 --trakt-client-id 或设置环境变量 TRAKT_CLIENT_ID。")
    if not token and args.type == "watched":
        # watchlist 写入可不带 token？（Trakt 也需要授权，这里统一要求）
        raise SystemExit("缺少 Trakt Access Token。请使用 --trakt-token、设置环境变量 TRAKT_ACCESS_TOKEN，或提供 token.json。")

    migrate_from_csv(args.csv, args.type, client_id, token, args.dry_run)

if __name__ == "__main__":
    main()
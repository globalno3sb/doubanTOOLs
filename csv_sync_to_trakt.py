# -*- coding: utf-8 -*-
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone, timedelta

import requests
import certifi

# ========= 默认配置（可被命令行覆盖/或用 token.json）=========
TRAKT_CLIENT_ID_DEFAULT = ""
TRAKT_ACCESS_TOKEN_FALLBACK = ""
BATCH_SIZE = 80
REQUEST_TIMEOUT = 30
# =========================================================


def load_trakt_access_token():
    """
    优先从当前目录 token.json 读取 {"access_token": "..."}，
    否则返回 fallback（不建议长期使用 fallback）。
    """
    token_path = os.path.join(os.path.dirname(__file__), "token.json")
    if os.path.exists(token_path):
        try:
            with open(token_path, "r") as f:
                data = json.load(f)
                if "access_token" in data and data["access_token"]:
                    return data["access_token"]
        except Exception:
            pass
    return TRAKT_ACCESS_TOKEN_FALLBACK


def convert_local_cn_to_utc_iso(dt_str: str) -> str | None:
    """
    把 CSV 中的 datetime（形如 'YYYY-MM-DD HH:MM:SS'，按 UTC+8 理解）转成 UTC ISO8601。
    不符合格式则返回 None。
    """
    if not dt_str:
        return None
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        tz_cn = timezone(timedelta(hours=8))
        dt_cn = dt.replace(tzinfo=tz_cn)
        dt_utc = dt_cn.astimezone(timezone.utc)
        return dt_utc.isoformat()
    except Exception:
        return None


def post_trakt_sync(endpoint: str, payload: dict, access_token: str, client_id: str):
    url = f"https://api.trakt.tv/sync/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
        "User-Agent": "Mozilla/5.0",
    }
    r = requests.post(
        url, headers=headers, json=payload,
        verify=certifi.where(), timeout=REQUEST_TIMEOUT
    )
    return r


def read_csv_rows(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV 不存在: {path}")
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        # 这里不强校验表头顺序，只要包含所需字段即可
        need = {"title","date","datetime","type","season","slug","matched_title","matched_year","found","douban_link"}
        if not need.issubset(set(r.fieldnames or [])):
            raise ValueError(f"CSV 表头缺少: {need - set(r.fieldnames or [])}；当前表头={r.fieldnames}")
        for row in r:
            rows.append(row)
    return rows


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


def build_movie_entries(pairs, watched_mode):
    out = []
    for slug, w in pairs:
        e = {"ids": {"slug": slug}}
        if watched_mode and w:
            e["watched_at"] = w
        out.append(e)
    return out


def build_show_season_entries(pairs, watched_mode):
    """
    pairs: [(slug, season_no(int), watched_iso or None), ...]
    聚合到 Trakt 的 shows:[{ids:{}, seasons:[{number, watched_at?}, ...]}]
    """
    agg = {}
    for slug, sn, w in pairs:
        agg.setdefault(slug, {})
        if sn not in agg[slug]:
            agg[slug][sn] = w
    result = []
    for slug, seasons in agg.items():
        seasons_payload = []
        for sn, w in seasons.items():
            obj = {"number": int(sn)}
            if watched_mode and w:
                obj["watched_at"] = w
            seasons_payload.append(obj)
        result.append({"ids": {"slug": slug}, "seasons": seasons_payload})
    return result


def migrate_from_csv(args):
    # client_id 优先命令行，其次默认
    client_id = args.trakt_client_id or TRAKT_CLIENT_ID_DEFAULT
    access_token = args.trakt_token or load_trakt_access_token()

    rows = read_csv_rows(args.csv)
    print(f"已读取 CSV：{args.csv}，共 {len(rows)} 条。")

    movies = []
    show_seasons = []
    show_whole = []

    for row in rows:
        # 仅导入 found==1 的匹配结果（避免误写）
        found = (row.get("found") or "").strip()
        if found not in ("1", "true", "True", "yes", "Y"):
            continue

        slug = (row.get("slug") or "").strip()
        typ = (row.get("type") or "").strip().lower()
        season = (row.get("season") or "").strip()
        dt_local = (row.get("datetime") or "").strip()

        if not slug or not typ:
            continue

        watched_iso = convert_local_cn_to_utc_iso(dt_local)

        if typ == "movie":
            movies.append((slug, watched_iso))
        elif typ == "show":
            if season and season.isdigit():
                show_seasons.append((slug, int(season), watched_iso))
            else:
                show_whole.append((slug, watched_iso))
        # 其他类型忽略

    print(f"汇总：movies={len(movies)}，show(seasons)={len(show_seasons)}，show(no-season)={len(show_whole)}")

    if args.dry_run:
        print("DRY-RUN 模式：只展示 payload，不提交。")
        for group in chunks(movies, BATCH_SIZE):
            payload = {"movies": build_movie_entries(group, watched_mode=(args.type=="watched"))}
            print(json.dumps(payload, indent=2, ensure_ascii=False)[:400])
        for group in chunks(show_seasons, BATCH_SIZE):
            payload = {"shows": build_show_season_entries(group, watched_mode=(args.type=="watched"))}
            print(json.dumps(payload, indent=2, ensure_ascii=False)[:400])
        if show_whole:
            preview = [{"ids": {"slug": s}, **({"watched_at": w} if (args.type=="watched" and w) else {})}
                       for (s, w) in show_whole[:min(10, len(show_whole))]]
            print(json.dumps({"shows": preview}, indent=2, ensure_ascii=False))
        return

    # 真正提交
    if args.type == "watched":
        for group in chunks(movies, BATCH_SIZE):
            payload = {"movies": build_movie_entries(group, watched_mode=True)}
            r = post_trakt_sync("history", payload, access_token, client_id)
            print(f"[history/movies] -> {r.status_code} {r.text[:200]}")
            time.sleep(1.2)

        for group in chunks(show_seasons, BATCH_SIZE):
            payload = {"shows": build_show_season_entries(group, watched_mode=True)}
            r = post_trakt_sync("history", payload, access_token, client_id)
            print(f"[history/shows(seasons)] -> {r.status_code} {r.text[:200]}")
            time.sleep(1.2)

        if show_whole:
            print("无季号的 show 以 show 级别写入 history 可能不生效（建议补季号后再导入）。")
            for group in chunks(show_whole, BATCH_SIZE):
                entries = []
                for slug, w in group:
                    obj = {"ids": {"slug": slug}}
                    if w:
                        obj["watched_at"] = w
                    entries.append(obj)
                payload = {"shows": entries}
                r = post_trakt_sync("history", payload, access_token, client_id)
                print(f"[history/shows(no-season)] -> {r.status_code} {r.text[:200]}")
                time.sleep(1.2)

    else:  # watchlist
        for group in chunks(movies, BATCH_SIZE):
            payload = {"movies": build_movie_entries(group, watched_mode=False)}
            r = post_trakt_sync("watchlist", payload, access_token, client_id)
            print(f"[watchlist/movies] -> {r.status_code} {r.text[:200]}")
            time.sleep(1.2)

        shows_all = [(slug, w) for (slug, _, w) in show_seasons] + show_whole
        for group in chunks(shows_all, BATCH_SIZE):
            entries = [{"ids": {"slug": slug}} for slug, _ in group]
            payload = {"shows": entries}
            r = post_trakt_sync("watchlist", payload, access_token, client_id)
            print(f"[watchlist/shows] -> {r.status_code} {r.text[:200]}")
            time.sleep(1.2)

    print("同步完成。")


def main():
    p = argparse.ArgumentParser(description="根据新格式 CSV 同步到 Trakt")
    p.add_argument("--csv", required=True, help="CSV 文件路径（title,date,datetime,type,season,slug,matched_title,matched_year,found,douban_link）")
    p.add_argument("-t", "--type", choices=["watched","watchlist"], required=True,
                   help="watched => /sync/history；watchlist => /sync/watchlist")

    # 可选：命令行覆盖 Trakt 凭据（否则用默认/或 token.json）
    p.add_argument("--trakt-client-id", default=None, help="Trakt Client ID（可选，默认用内置）")
    p.add_argument("--trakt-token", default=None, help="Trakt Access Token（可选，默认读 token.json 或 fallback）")

    p.add_argument("--dry-run", action="store_true", help="只生成 payload，不写入 Trakt")
    args = p.parse_args()
    migrate_from_csv(args)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
from io_csv import read_csv_rows, chunks
from time_utils import convert_local_cn_to_utc_iso
from trakt import (
    post_trakt_sync, build_movie_entries, build_show_season_entries, preview_payload
)
import time

BATCH_SIZE = 80

def migrate_from_csv(csv_path: str, mode: str, client_id: str, access_token: str, dry_run: bool):
    """
    mode: "watched" | "watchlist"
    """
    rows = read_csv_rows(csv_path)
    print(f"已读取 CSV：{csv_path}，共 {len(rows)} 条。")

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

    print(f"汇总：movies={len(movies)}，show(seasons)={len(show_seasons)}，show(no-season)={len(show_whole)}")

    if dry_run:
        print("DRY-RUN 预览：")
        print(preview_payload(movies, show_seasons, show_whole, mode))
        return

    # 提交
    if mode == "watched":
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
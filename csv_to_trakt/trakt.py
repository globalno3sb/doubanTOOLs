# -*- coding: utf-8 -*-
import certifi
import json
import requests

REQUEST_TIMEOUT = 30

def post_trakt_sync(endpoint: str, payload: dict, access_token: str, client_id: str):
    """
    endpoint: "history" | "watchlist"
    """
    url = f"https://api.trakt.tv/sync/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
        "User-Agent": "Mozilla/5.0",
    }
    return requests.post(
        url, headers=headers, json=payload,
        verify=certifi.where(), timeout=REQUEST_TIMEOUT
    )

def build_movie_entries(pairs, watched_mode: bool):
    """
    pairs: [(slug, watched_iso_or_None), ...]
    """
    out = []
    for slug, w in pairs:
        e = {"ids": {"slug": slug}}
        if watched_mode and w:
            e["watched_at"] = w
        out.append(e)
    return out

def build_show_season_entries(pairs, watched_mode: bool):
    """
    pairs: [(slug, season_no(int), watched_iso_or_None), ...]
    → shows: [{ids:{slug}, seasons:[{number, watched_at?}, ...]}, ...]
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

def preview_payload(movies, show_seasons, show_whole, mode: str):
    """
    仅用于 --dry-run 的友好输出
    """
    pre = {}
    if movies:
        pre["movies"] = build_movie_entries(movies, watched_mode=(mode=="watched"))
    if show_seasons:
        pre["shows(seasons)"] = build_show_season_entries(show_seasons, watched_mode=(mode=="watched"))
    if show_whole:
        pre["shows(no-season)"] = [
            {"ids": {"slug": s}, **({"watched_at": w} if (mode=="watched" and w) else {})}
            for (s, w) in show_whole[:min(10, len(show_whole))]
        ]
    return json.dumps(pre, indent=2, ensure_ascii=False)
# -*- coding: utf-8 -*-
"""
enrich_csv_times.py
读取已有 CSV → 通过 m.douban.com interests 拉取 create_time/type → 为每行补更精确的时间与类型 → 写回 CSV

CSV 读写规则：
- 读取时优先使用列：title,date,datetime,douban_link,datetime_refined,douban_type,douban_subject_id
- 如无 douban_subject_id，会从 douban_link 提取 subject id
- 输出时确保包含：datetime_refined、douban_type、douban_subject_id（其他原有列一律保留）

使用示例：
  仅为“时间为 00:00:00 或无”的项目补时，输出新文件：
    python3 enrich_csv_times.py --in movie.csv --out movie_refined.csv --user-id 236764164 --only-missing

  覆盖原文件（小心）：
    python3 enrich_csv_times.py --in movie.csv --inplace --user-id 236764164

  指定拉取的状态（默认 done,do,mark,wish）：
    python3 enrich_csv_times.py --in movie.csv --out movie_refined.csv --user-id 236764164 --statuses done do mark
"""
import argparse
import csv
import os
import re
import time
import random
from datetime import datetime
from typing import Dict, List, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

# ------- HTTP session with retry -------
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://m.douban.com/mine/movie",
    "Connection": "keep-alive",
})
_retry = Retry(
    total=6,
    connect=3,
    read=5,
    status=5,
    backoff_factor=1.2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET"]),
    raise_on_status=False,
)
_adapter = HTTPAdapter(max_retries=_retry, pool_connections=20, pool_maxsize=40)
SESSION.mount("https://", _adapter)
SESSION.mount("http://", _adapter)

SUBJECT_ID_RE = re.compile(r"/subject/(\d+)/?")

def extract_subject_id(link: str):
    if not link:
        return None
    m = SUBJECT_ID_RE.search(link)
    return m.group(1) if m else None

def pull_interests_map_all_status(
    user_id: str,
    statuses: List[str],
    sleep_base: float = 0.2,
    count: int = 100,
    verbose: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """
    拉取多个 status 的 interests，合并为：
    sid -> {"type": "movie"/"show", "times": ["YYYY-MM-DD HH:MM:SS", ...（新在前）]}
    """
    base = f"https://m.douban.com/rexxar/api/v2/user/{user_id}/interests"
    all_map: Dict[str, Dict[str, Any]] = {}
    if verbose:
        print(f"拉取豆瓣移动端 create_time/type 映射（{','.join(statuses)}）...")

    def merge_item(subj_id: str, raw_type: str, create_time: str):
        if not subj_id or not create_time:
            return
        typ = "movie" if (raw_type or "").lower() == "movie" else "show"
        bucket = all_map.setdefault(subj_id, {"type": typ, "times": []})
        bucket["type"] = typ  # 以最新出现为准
        if create_time not in bucket["times"]:
            bucket["times"].append(create_time)

    for status in statuses:
        if verbose:
            print(f"  ▶ status={status}")
        start = 0
        empty_in_a_row = 0
        while True:
            params = {"status": status, "start": start, "count": count}
            ok = False
            try:
                r = SESSION.get(base, params=params, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    arr = data.get("interests", []) or []
                    ok = True
                else:
                    arr = []
            except Exception:
                arr = []

            if not ok:
                empty_in_a_row += 1
            else:
                if not arr:
                    empty_in_a_row += 1
                else:
                    empty_in_a_row = 0
                    for it in arr:
                        subj = it.get("subject") or {}
                        sid = str(subj.get("id") or "").strip()
                        raw_type = (subj.get("type") or "").strip()
                        create_time = it.get("create_time") or ""
                        merge_item(sid, raw_type, create_time)
                start += count

            if empty_in_a_row >= 3:
                break

            time.sleep(sleep_base + random.random() * sleep_base)

        if verbose:
            print(f"    · 聚合后 unique subjects：{len(all_map)}")

    # times 按时间倒序（最近在前）
    for sid, v in all_map.items():
        try:
            v["times"].sort(key=lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S"), reverse=True)
        except Exception:
            pass

    if verbose:
        print(f"映射完成，unique subjects={len(all_map)}")
    return all_map

def pick_best_time(times_list: List[str], date_str: str) -> str | None:
    """
    在 times_list 中选一条最接近页面 date（同一天优先；否则日期距离最小；若相同取更晚）。
    """
    if not times_list:
        return None
    if not date_str:
        return times_list[0]
    try:
        target_day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return times_list[0]

    best = None
    best_metric = None
    for ts in times_list:
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            distance = abs((dt.date() - target_day).days)
            metric = (distance, -dt.timestamp())  # 距离小优先；同距离更晚优先（timestamp 取负）
            if best_metric is None or metric < best_metric:
                best_metric = metric
                best = ts
        except Exception:
            continue
    return best or times_list[0]

def read_csv_rows(path: str) -> List[dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV 不存在: {path}")
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r)

def write_csv_rows(path: str, rows: List[dict], fieldnames: List[str]):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow(row)

def ensure_cols(row: dict, keys: List[str]):
    for k in keys:
        row.setdefault(k, "")

def should_refine(row: dict, only_missing: bool) -> bool:
    """是否需要补时：only_missing=True 时，仅当没有 datetime_refined 或以 00:00:00 结尾"""
    dt_ref = (row.get("datetime_refined") or "").strip()
    if not only_missing:
        return True
    if not dt_ref:
        return True
    return dt_ref.endswith("00:00:00")

def main():
    ap = argparse.ArgumentParser(description="读取 CSV，使用豆瓣 interests 补时间/类型，然后写回 CSV")
    ap.add_argument("--in", dest="inp", required=True, help="输入 CSV 路径")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--out", help="输出为新 CSV 路径")
    g.add_argument("--inplace", action="store_true", help="原地覆盖（谨慎）")
    ap.add_argument("--user-id", required=True, help="豆瓣用户 ID，用于拉取 interests")
    ap.add_argument("--statuses", nargs="+", default=["done", "do", "mark", "wish"],
                    help="拉取的状态集合，默认：done do mark wish")
    ap.add_argument("--only-missing", action="store_true",
                    help="只补没有 datetime_refined 或以 00:00:00 结尾的记录")
    ap.add_argument("--midday-fallback", action="store_true",
                    help="若无法从 interests 补时，则将 datetime_refined 设为 `date 12:00:00`（默认不启用）")
    ap.add_argument("--verbose", action="store_true", help="打印详细过程")
    args = ap.parse_args()

    rows = read_csv_rows(args.inp)
    if args.verbose:
        print(f"读取 CSV：{args.inp}，共 {len(rows)} 条")

    # 拉映射
    interests_map = pull_interests_map_all_status(
        user_id=args.user_id,
        statuses=args.statuses,
        verbose=args.verbose,
    )

    updated = 0
    untouched = 0

    # 确保关键列存在
    # 动态保留原表头，额外并入新列
    orig_fields = list(rows[0].keys()) if rows else []
    extra_fields = ["datetime_refined", "douban_type", "douban_subject_id"]
    fieldnames = list(dict.fromkeys(orig_fields + extra_fields))  # 去重保序

    for row in rows:
        ensure_cols(row, extra_fields)
        title = (row.get("title") or "").strip()
        date_str = (row.get("date") or "").strip()
        dt_orig = (row.get("datetime") or "").strip()
        dt_refined = (row.get("datetime_refined") or "").strip()
        link = (row.get("douban_link") or "").strip()
        sid = (row.get("douban_subject_id") or "").strip() or extract_subject_id(link) or ""

        # 回填 subject_id（若之前为空）
        row["douban_subject_id"] = sid

        if not should_refine(row, args.only_missing):
            untouched += 1
            continue

        best_time = None
        typ = (row.get("douban_type") or "").strip()

        if sid and sid in interests_map:
            item = interests_map[sid]
            times = item.get("times") or []
            best_time = pick_best_time(times, date_str)
            typ = item.get("type") or (typ or "")
        else:
            if args.verbose and title:
                print(f"  无映射：{title} (sid={sid})")

        # 回填类型（尽量）
        if not typ:
            typ = "movie"
        row["douban_type"] = typ

        # 确定 datetime_refined
        if best_time:
            row["datetime_refined"] = best_time
            updated += 1
        else:
            # 无法补时 → 是否使用中午兜底
            if args.midday_fallback and date_str:
                row["datetime_refined"] = f"{date_str} 12:00:00"
                updated += 1
            else:
                # 保留原值（如果原来也为空则为空）
                row["datetime_refined"] = dt_refined or dt_orig
                if row["datetime_refined"]:
                    untouched += 1

    out_path = args.out if args.out else args.inp
    if args.inplace:
        out_path = args.inp

    write_csv_rows(out_path, rows, fieldnames)
    print(f"写出：{out_path}  （更新 {updated} 条，保留 {untouched} 条）")

if __name__ == "__main__":
    main()

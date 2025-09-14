# -*- coding: utf-8 -*-
import csv
import os

REQUIRED_FIELDS = {
    "title","date","datetime","type","season","slug",
    "matched_title","matched_year","found","douban_link"
}

def read_csv_rows(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV 不存在: {path}")
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if not REQUIRED_FIELDS.issubset(set(r.fieldnames or [])):
            raise ValueError(f"CSV 表头缺少: {REQUIRED_FIELDS - set(r.fieldnames or [])}；当前表头={r.fieldnames}")
        for row in r:
            rows.append(row)
    return rows

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]
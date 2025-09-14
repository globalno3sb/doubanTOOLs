# -*- coding: utf-8 -*-
import argparse
import csv
import os
import re
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
import certifi
from bs4 import BeautifulSoup

# ====== 你的 Edge 配置（复用登录态）======
EDGE_DRIVER = "/path/to/edgedriver"
EDGE_PROFILE_DIR = "/path/to/selenium_profile"  # Selenium 用户数据目录

# ====== 请求会话 ======
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
})

# ====== Selenium 准备 ======
_driver = None
def get_driver():
    global _driver
    if _driver is not None:
        return _driver
    from selenium import webdriver
    from selenium.webdriver.edge.service import Service
    from selenium.webdriver.edge.options import Options

    opts = Options()
    # 复用你已有的独立登录态目录
    opts.add_argument(f"--user-data-dir={EDGE_PROFILE_DIR}")
    opts.add_argument("--profile-directory=Default")
    service = Service(EDGE_DRIVER)
    _driver = webdriver.Edge(service=service, options=opts)
    return _driver

def sync_driver_cookies_to_session(domains=None):
    """将 Edge 浏览器 Cookie 同步至 requests.Session，兼容主域与子域"""
    driver = get_driver()
    cookies = driver.get_cookies()
    SESSION.cookies.clear()
    if not domains:
        domains = [".douban.com", "www.douban.com", "movie.douban.com", "m.douban.com"]
    for c in cookies:
        name = c.get("name"); value=c.get("value")
        if not name: continue
        for d in domains:
            try:
                SESSION.cookies.set(name, value, domain=d, path="/")
            except Exception:
                pass

def ensure_login_ready():
    """打开一个页面触发登录/验证码，完成后回车继续"""
    driver = get_driver()
    driver.get("https://movie.douban.com/")
    time.sleep(2)
    html = driver.page_source.lower()
    need_manual = any(k in html for k in ["验证码","人机验证","请先登录","sec.douban.com","/misc/sorry"])
    if need_manual:
        input("需要你在浏览器里手动完成登录/验证，完毕后按回车继续...")
    sync_driver_cookies_to_session()

# ====== Douban API 猜测端点（有就赚，没有就跳过）======
def api_user_interest_single(user_id: str, subject_id: str):
    """
    猜测的单条兴趣接口：/rexxar/api/v2/user/{uid}/interest?subject_id=SID
    有时候返回:
      {"create_time":"2023-07-28 21:32:11", ...}
    也可能 404/无此字段 → 返回 None
    """
    url = f"https://m.douban.com/rexxar/api/v2/user/{user_id}/interest"
    try:
        r = SESSION.get(url, params={"subject_id": subject_id}, timeout=20, verify=certifi.where())
        if r.status_code != 200:
            return None
        data = r.json()
        ct = data.get("create_time")
        return ct if (ct and re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", ct)) else None
    except Exception:
        return None

def api_mobile_subject(subject_id: str):
    """
    移动端主题页：/rexxar/api/v2/subject/{sid}?for_mobile=1
    部分账号/时段会在附带的 interest or activities 里出现用户时间；不保证一定有。
    """
    url = f"https://m.douban.com/rexxar/api/v2/subject/{subject_id}"
    try:
        r = SESSION.get(url, params={"for_mobile": "1"}, timeout=20, verify=certifi.where())
        if r.status_code != 200:
            return None
        data = r.json()
        # 尝试几种常见位置（并不严格，尽力而为）
        for key in ("interest", "user_interest", "activity", "activities"):
            val = data.get(key)
            if isinstance(val, dict):
                ct = val.get("create_time")
                if ct and re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", ct):
                    return ct
            elif isinstance(val, list):
                # 找里面最近的一条（演示性质）
                for it in val:
                    ct = (it or {}).get("create_time")
                    if ct and re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", ct):
                        return ct
        return None
    except Exception:
        return None

# ====== 桌面主题页抓“我的标记/我的评价”具体时间 ======
def scrape_subject_page_for_time(douban_link: str):
    """
    用已登录的浏览器打开主题页，尽力在“我的标记/我的评价”处找具体时间。
    注意：很多条目只有“日期”，没有“分秒”；找不到就返回 None。
    """
    driver = get_driver()
    driver.get(douban_link)
    time.sleep(1.8)
    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")

    # 这里按几种常见 DOM 尝试（豆瓣随时改版，匹配尽力即可）
    # 1) 用户操作时间（可能在“我的评价/我看过”区域）
    #   例：<span class="created_at">2023-07-21 22:31:15</span>
    cand = soup.find("span", class_=re.compile(r"(created_at|create_time|status-time|rating-date|date)"))
    if cand:
        text = cand.get_text(strip=True)
        if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text):
            return text

    # 2) 某些新版把“时间”放在 title 属性或 data-* 属性里
    for tag in soup.find_all(["span","time"], attrs=True):
        # title 或 data-created 等
        for k,v in list(tag.attrs.items()):
            if isinstance(v, str) and re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", v):
                return v

    return None

# ====== CSV I/O ======
def read_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows.extend(r)
    return rows, r.fieldnames

def write_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def needs_refine(dt_str: str) -> bool:
    if not dt_str:
        return True
    return dt_str.endswith("00:00:00") or dt_str.endswith("12:00:00")

def extract_subject_id(douban_link: str):
    if not douban_link: return None
    m = re.search(r"/subject/(\d+)", douban_link)
    return m.group(1) if m else None

# ====== 主流程 ======
def main():
    ap = argparse.ArgumentParser(description="对已有 CSV 逐条补时：尽量补齐精确到秒的 create_time；失败则保留原值。")
    ap.add_argument("--in", dest="inp", required=True, help="输入 CSV（包含 datetime 和 douban_link 列）")
    ap.add_argument("--out", dest="outp", required=True, help="输出 CSV（就地覆盖可与 --in 相同）")
    ap.add_argument("--user-id", required=True, help="豆瓣用户 ID（用于接口 A）")
    ap.add_argument("--backup", action="store_true", help="写出前生成 .bak 备份")
    ap.add_argument("--limit", type=int, default=None, help="最多处理多少条需要补时的记录（调试用）")
    args = ap.parse_args()

    rows, headers = read_csv(args.inp)
    if "datetime" not in headers or "douban_link" not in headers:
        raise SystemExit("CSV 缺少 datetime / douban_link 字段。")

    print(f"读取：{args.inp}  共 {len(rows)} 条。")
    print("启动浏览器以复用登录态...（若弹出验证码/登录，请完成后回车）")
    ensure_login_ready()

    updated = 0
    total_need = [r for r in rows if needs_refine(r.get("datetime",""))]
    print(f"需尝试补时的记录：{len(total_need)} 条")

    for idx, row in enumerate(rows, start=1):
        dt0 = row.get("datetime","") or ""
        if not needs_refine(dt0):
            continue

        sid = extract_subject_id(row.get("douban_link","") or "")
        refined = None

        # A) 单条兴趣接口（命中即止）
        if sid:
            refined = api_user_interest_single(args.user_id, sid)

        # B) 移动端主题页 JSON
        if not refined and sid:
            refined = api_mobile_subject(sid)

        # C) 桌面主题页（最后再试）
        if not refined and row.get("douban_link"):
            refined = scrape_subject_page_for_time(row["douban_link"])

        # 更新
        if refined:
            row["datetime"] = refined
            updated += 1

        # 限速 & 调试 limit
        time.sleep(0.3)
        if args.limit and updated >= args.limit:
            break

        # 简要进度
        if idx % 50 == 0:
            print(f"  ...处理进度 {idx}/{len(rows)}，已更新 {updated} 条")

    # 备份
    if args.backup and os.path.abspath(args.inp) == os.path.abspath(args.outp):
        bak = args.inp + ".bak"
        with open(bak, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader(); w.writerows(rows)
        print(f"已写入备份：{bak}")

    write_csv(args.outp, rows, headers)
    print(f"写出：{args.outp}  （更新 {updated} 条，保留 {len(rows)-updated} 条）")

if __name__ == "__main__":
    main()

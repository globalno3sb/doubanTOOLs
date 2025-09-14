import re, time
from datetime import datetime, timedelta, timezone, date
from bs4 import BeautifulSoup
from session_utils import fetch, fetch_json, polite_sleep, SESSION
import config

SUBJECT_ID_RE = re.compile(r"/subject/(\d+)/?")

# ========== 类型与季号识别 ==========

_CN_NUM = {"零":0,"〇":0,"一":1,"二":2,"两":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
def _cn_num_to_int(s):
    if not s: return None
    if s in _CN_NUM: return _CN_NUM[s]
    if "十" in s:
        a,b = s.split("十") if "十" in s else ("","")
        a = _CN_NUM.get(a,1 if a=="" else 0)
        b = _CN_NUM.get(b,0)
        return a*10+b
    return None

SEASON_PATTERNS = [
    re.compile(r"[第\s]*(\d+)\s*季"),
    re.compile(r"[第\s]*([一二三四五六七八九十两〇零]+)\s*季"),
    re.compile(r"[Ss]eason\s*(\d+)"),
    re.compile(r"[Ss]\s?(\d+)\b"),
    re.compile(r"[第\s]*([一二三四五六七八九十两〇零]+)\s*部"),
    re.compile(r"[Pp]art\s*(\d+)")
]

def extract_season_number(title:str):
    for pat in SEASON_PATTERNS:
        m = pat.search(title or "")
        if m:
            g = m.group(1)
            if g.isdigit(): return int(g)
            v = _cn_num_to_int(g)
            if v: return v
    return None

def fallback_detect_type(title:str)->str:
    if extract_season_number(title):
        return "show"
    if re.search(r"(第\s*[一二三四五六七八九十两〇零\d]+\s*话)|TV|电视剧|ドラマ|Season", title, re.IGNORECASE):
        return "show"
    return "movie"

def extract_subject_id(link:str):
    if not link: return None
    m = SUBJECT_ID_RE.search(link)
    return m.group(1) if m else None

def map_douban_type(raw:str)->str:
    if not raw: return None
    raw=raw.lower()
    if "tv" in raw or "show" in raw or "series" in raw or "剧" in raw:
        return "show"
    if "movie" in raw or "film" in raw:
        return "movie"
    return None

# ========== 补时间 ==========

def get_interests_map(user_id:str):
    """批量拉取 m 端兴趣表，包含 create_time 和 type"""
    base=f"https://m.douban.com/rexxar/api/v2/user/{user_id}/interests"
    start=0; count=100
    mapping={}
    while True:
        params={"status":"done","start":start,"count":count}
        js=fetch_json(base,params=params,referer="https://m.douban.com/mine/movie")
        if not js: break
        arr=js.get("interests",[])
        if not arr: break
        for it in arr:
            subj=it.get("subject") or {}
            sid=str(subj.get("id") or "").strip()
            if not sid: continue
            raw= subj.get("type") or ""
            mapping[sid]={"create_time":it.get("create_time") or "","douban_type":map_douban_type(raw) or ""}
        start+=count
        time.sleep(0.2)
    return mapping

def fetch_subject_detail(subject_id:str)->dict:
    url=f"https://m.douban.com/rexxar/api/v2/subject/{subject_id}"
    js=fetch_json(url,params={"for_mobile":"1"})
    if not js: return {}
    st= map_douban_type(js.get("type") or "")
    ct=None
    for key in ("interest","user_interest","activity","activities"):
        v=js.get(key)
        if isinstance(v,dict):
            ct=v.get("create_time") or None
        elif isinstance(v,list) and v:
            cand=v[0].get("create_time")
            if cand: ct=cand
        if ct: break
    return {"type":st,"create_time":ct}

def refine_datetime(row,interests_map,user_id,deep_refine=False,deep_days=None):
    sid=extract_subject_id(row.get("douban_link",""))
    today=date.today()
    dt=None
    typ=row.get("type") or "movie"
    if sid and sid in interests_map:
        meta=interests_map[sid]
        if meta.get("create_time"): dt=meta["create_time"]
        if meta.get("douban_type"): typ=meta["douban_type"]

    if not dt and row.get("date"):
        dt=f"{row['date']} 12:00:00"

    need_deep= deep_refine and (not dt or dt.endswith("12:00:00"))
    if need_deep and sid:
        if deep_days is not None and row.get("date"):
            try:
                d0=datetime.strptime(row["date"],"%Y-%m-%d").date()
                if (today-d0).days>deep_days:
                    need_deep=False
            except: pass
    if need_deep:
        det=fetch_subject_detail(sid)
        if det.get("create_time"): dt=det["create_time"]
        if det.get("type"): typ=det["type"]

    if not typ: typ=fallback_detect_type(row.get("title",""))
    season= extract_season_number(row.get("title",""))
    row.update({
        "datetime": dt or "",
        "type": typ,
        "season": str(season or ""),
    })
    return row
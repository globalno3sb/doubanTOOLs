import time, re
import requests, certifi
import config
from session_utils import polite_sleep

def normalize_title(title:str):
    t=title or ""
    # 去掉季号
    t=re.sub(r"\s*[第\s]*\d+\s*季","",t)
    t=re.sub(r"\s*[第\s]*[一二三四五六七八九十两〇零]+\s*季","",t)
    t=re.sub(r"\s*[Ss]eason\s*\d+","",t)
    t=re.sub(r"\s*[Ss]\s?\d+\b","",t)
    t=re.sub(r"\s*[第\s]*[一二三四五六七八九十两〇零]+\s*部","",t)
    t=re.sub(r"\s*[Pp]art\s*\d+","",t)
    return t.strip(" ·-—:：()（）")

def search_trakt(title:str,year_hint:str,typ:str,client_id:str):
    url=f"https://api.trakt.tv/search/{typ}"
    headers={"trakt-api-version":"2","trakt-api-key":client_id,"User-Agent":"Mozilla/5.0"}
    for q in (normalize_title(title),title):
        try:
            r=requests.get(url,params={"query":q},headers=headers,timeout=config.REQUEST_TIMEOUT,verify=certifi.where())
        except Exception as e:
            print(f"[ERROR] Trakt请求失败 {e}")
            continue
        if r.status_code!=200:
            continue
        try:
            items=r.json()
        except Exception:
            items=[]
        if not items:
            continue
        if year_hint and year_hint.isdigit():
            y=int(year_hint)
            for it in items:
                obj=it.get(typ) or {}
                yy=obj.get("year")
                if yy and yy-1<=y<=yy+1:
                    slug=(obj.get("ids") or {}).get("slug")
                    if slug:
                        return slug,obj.get("title") or "",yy
        obj0=items[0].get(typ) or {}
        slug=(obj0.get("ids") or {}).get("slug")
        if slug: return slug,obj0.get("title") or "",obj0.get("year")
        polite_sleep()
    return None,None,None
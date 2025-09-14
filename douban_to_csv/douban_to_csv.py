#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, argparse, time, random
from datetime import datetime
from bs4 import BeautifulSoup

# Handle imports for standalone script execution
from douban import get_interests_map, refine_datetime, extract_subject_id, fallback_detect_type
from session_utils import fetch, polite_sleep
from trakt import search_trakt
import config
from exporter import save_csv

IS_OVER=False

def get_max_page(user_id):
    url=f"https://movie.douban.com/people/{user_id}/collect"
    html=fetch(url,referer="https://movie.douban.com/")
    soup=BeautifulSoup(html,"lxml")
    p=soup.find("div",{"class":"paginator"})
    if p and p.find_all("a"):
        try: return int(p.find_all("a")[-2].get_text())
        except: return 1
    return 1

def parse_collect_page(url,interests_map,user_id,deep_refine,deep_days,start_date,client_id):
    global IS_OVER
    html=fetch(url,referer="https://movie.douban.com/")
    if not html: return []
    soup=BeautifulSoup(html,"lxml")
    items=soup.find_all("div",{"class":"item"})
    out=[]
    for it in items:
        a=it.find("a")
        if not a or not a.get("href"): continue
        link=a["href"].strip()
        sid=extract_subject_id(link)

        title= (it.find("li",{"class":"title"}).em.get_text(strip=True)
                if it.find("li",{"class":"title"}) else "")
        date_span=it.find("span",{"class":"date"})
        date_str=date_span.get_text(strip=True) if date_span else ""
        if date_str:
            try:
                if datetime.strptime(date_str,"%Y-%m-%d")<=datetime.strptime(start_date,"%Y%m%d"):
                    IS_OVER=True
                    break
            except: pass

        row={"title":title,"date":date_str,"datetime":f"{date_str} 12:00:00","type":fallback_detect_type(title),
             "season":"","slug":"","matched_title":"","matched_year":"","found":"0","douban_link":link}
        row=refine_datetime(row,interests_map,user_id,deep_refine,deep_days)

        year_hint=date_str[:4] if date_str else ""
        slug,mtitle,myear=search_trakt(row["title"],year_hint,row["type"],client_id)
        if slug:
            row.update({"slug":slug,"matched_title":mtitle,"matched_year":myear or "","found":"1"})
        out.append(row)
        polite_sleep()
    return out

def run(user_id,start_date,deep_refine,deep_days,client_id,outfile):
    global IS_OVER
    IS_OVER=False
    interests_map=get_interests_map(user_id)
    rows=[]
    maxp=get_max_page(user_id)
    page_no=1
    for idx in range(0,maxp*15,15):
        if IS_OVER: break
        url=f"https://movie.douban.com/people/{user_id}/collect?start={idx}&sort=time&rating=all&filter=all&mode=grid"
        print(f"抓取第 {page_no} 页...")
        data=parse_collect_page(url,interests_map,user_id,deep_refine,deep_days,start_date,client_id)
        rows.extend(data)
        print(f"  -> {len(data)} 条")
        page_no+=1
        time.sleep(0.6+random.random()*0.5)
    save_csv(rows,outfile)

def main():
    p=argparse.ArgumentParser(description="豆瓣观影记录抓取+Trakt匹配导出CSV")
    p.add_argument("user_id",help="豆瓣用户ID")
    p.add_argument("start_date",nargs="?",default="20050502",help="起始日期yyyyMMdd（默认全部）")
    p.add_argument("--deep-refine",action="store_true",help="是否启用单条兜底补时")
    p.add_argument("--deep-refine-window",type=int,default=None,help="只对最近N天内的记录做兜底补时")
    p.add_argument("--out",default="movie.csv",help="输出CSV路径")
    p.add_argument("--trakt-client-id",required=True,help="Trakt Client ID")
    args=p.parse_args()
    run(args.user_id,args.start_date,args.deep_refine,args.deep_refine_window,args.trakt_client_id,args.out)

if __name__=="__main__":
    main()
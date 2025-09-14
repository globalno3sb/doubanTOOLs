import csv, os

FIELDS=["title","date","datetime","type","season","slug","matched_title","matched_year","found","douban_link"]

def save_csv(rows:list,filename:str):
    path=os.path.abspath(filename)
    with open(path,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"保存至: {path} (共 {len(rows)} 条)")
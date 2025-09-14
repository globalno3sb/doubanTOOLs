import requests, random, time, os
import certifi
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": config.USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
})
_retry = Retry(total=6, connect=3, read=5, status=5, backoff_factor=1.2,
               status_forcelist=[429, 500, 502, 503, 504], allowed_methods=frozenset(["GET"]))
_adapter = HTTPAdapter(max_retries=_retry, pool_connections=20, pool_maxsize=40)
SESSION.mount("https://", _adapter)
SESSION.mount("http://", _adapter)

def fetch(url, params=None, timeout=config.REQUEST_TIMEOUT, referer=None):
    headers = {}
    if referer:
        headers["Referer"] = referer
    r = SESSION.get(url, params=params, headers=headers, timeout=timeout, verify=certifi.where())
    r.raise_for_status()
    return r.text

def fetch_json(url, params=None, timeout=config.REQUEST_TIMEOUT, referer=None):
    headers = {}
    if referer:
        headers["Referer"] = referer
    r = SESSION.get(url, params=params, headers=headers, timeout=timeout, verify=certifi.where())
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception:
        return None

def polite_sleep(base=0.35, jitter=0.45):
    time.sleep(base + random.random()*jitter)
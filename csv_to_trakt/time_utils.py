# -*- coding: utf-8 -*-
from datetime import datetime, timezone, timedelta

def convert_local_cn_to_utc_iso(dt_str: str) -> str | None:
    """
    把 CSV 中的 datetime（'YYYY-MM-DD HH:MM:SS'，按 UTC+8 理解）转成 UTC ISO8601。
    """
    if not dt_str:
        return None
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        tz_cn = timezone(timedelta(hours=8))
        dt_cn = dt.replace(tzinfo=tz_cn)
        dt_utc = dt_cn.astimezone(timezone.utc)
        return dt_utc.isoformat()
    except Exception:
        return None
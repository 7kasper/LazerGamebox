#!/usr/bin/env python3
"""Dump all JLC hits for a keyword (paged) to JSON. Usage: jlc_dump.py keyword out.json [maxpages]"""
import json, sys, urllib.request, time
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
kw, out = sys.argv[1], sys.argv[2]; maxp = int(sys.argv[3]) if len(sys.argv) > 3 else 20
allp = []
for page in range(1, maxp + 1):
    body = json.dumps({"currentPage":page,"pageSize":100,"keyword":kw,"searchSource":"search","componentLibraryType":"","stockFlag":True}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)["data"]["componentPageInfo"]
    lst = d["list"] or []
    allp += lst
    if len(lst) < 100: break
    time.sleep(0.5)
json.dump(allp, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print(kw, "->", len(allp), "parts")

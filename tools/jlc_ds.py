#!/usr/bin/env python3
"""Print datasheet URLs and details for exact LCSC codes. Usage: jlc_ds.py C123 C456 ..."""
import json, sys, urllib.request, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
for code in sys.argv[1:]:
    body = json.dumps({"currentPage":1,"pageSize":5,"keyword":code,"searchSource":"search","componentLibraryType":"","stockFlag":False}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        lst = json.load(r)["data"]["componentPageInfo"]["list"] or []
    hit = [p for p in lst if p["componentCode"] == code]
    if not hit: print(code, "NOT FOUND"); continue
    p = hit[0]
    lib = "BASIC" if p["componentLibraryType"] == "base" else ("PREF" if p.get("preferredComponentFlag") else "ext")
    pr = p["componentPrices"] or []
    print(f'{code} {lib} stock={p["stockCount"]} {p["componentBrandEn"]} {p["componentModelEn"]} | {p["componentSpecificationEn"]} | prices={[(t["startNumber"],t["productPrice"]) for t in pr]} | {p["dataManualUrl"]}')

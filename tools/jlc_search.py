#!/usr/bin/env python3
"""Query JLCPCB assembly parts library.
Usage: jlc_search.py [-n N] [-t TYPE_FILTER] [-a] keyword [keyword...]
  -n N   page size (default 8, max 100)
  -t X   only show rows whose category contains X (case-insensitive)
  -a     print attributes (package details) for each hit
"""
import json, sys, urllib.request, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
def search(kw, n=8, stock_only=True):
    body = json.dumps({"currentPage":1,"pageSize":n,"keyword":kw,"searchSource":"search",
                       "componentLibraryType":"","stockFlag":stock_only}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
    err = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)["data"]["componentPageInfo"]["list"] or []
        except Exception as e:
            err = e; time.sleep(2)
    print("ERR", kw, err); return []
def price(p, qty=25):
    pr = p.get("componentPrices") or []
    for t in pr:
        if t["startNumber"] <= qty and (t["endNumber"] == -1 or qty <= t["endNumber"]): return t["productPrice"]
    return pr[-1]["productPrice"] if pr else 0
def lib(p): return "BASIC" if p["componentLibraryType"] == "base" else ("PREF" if p.get("preferredComponentFlag") else "ext")
if __name__ == "__main__":
    args = sys.argv[1:]; n = 8; tf = None; attrs = False
    while args and args[0].startswith("-"):
        if args[0] == "-n": n = int(args[1]); args = args[2:]
        elif args[0] == "-t": tf = args[1].lower(); args = args[2:]
        elif args[0] == "-a": attrs = True; args = args[1:]
    for kw in args:
        print(f"=== {kw}")
        for p in search(kw, n):
            if tf and tf not in (p["componentTypeEn"] or "").lower(): continue
            print(f"  {p['componentCode']:<10} {lib(p):<5} stock={p['stockCount']:<7} ${price(p):<8.4f} {p['componentBrandEn']} {p['componentModelEn']} | {p['componentSpecificationEn']} | {p['componentTypeEn']}")
            if attrs:
                print("      " + "; ".join(f"{a['attribute_name_en']}={a['attribute_value_name']}" for a in p.get("attributes") or []))

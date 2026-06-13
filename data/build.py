#!/usr/bin/env python3
"""Merge the per-category raw centre files into a single deduped classes.json.

This is the seed of Bloom's data pipeline. Today the raw_*.json files are
produced by hand/agent research; a future weekly scan can regenerate them and
re-run this exact merge to refresh the live list.
"""
import json, glob, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REGION_ORDER = ["North", "North-East", "East", "West", "Central"]
# Conservative: only strip punctuation + legal suffixes. Better to leave two
# near-duplicate names unmerged than to fuse two genuinely different centres.
STOP = {"pte", "ltd"}


def norm_key(prov):
    s = prov.lower()
    s = re.sub(r"\(.*?\)", " ", s)          # drop parentheticals
    s = re.sub(r"[^a-z0-9 ]", " ", s)        # drop punctuation
    toks = [t for t in s.split() if t and t not in STOP]
    return " ".join(toks) or s.strip()


def order_regs(regs):
    seen = set()
    out = []
    for r in REGION_ORDER:
        if r in regs and r not in seen:
            out.append(r); seen.add(r)
    return out


def merge(a, b):
    """Merge b into a (a is kept)."""
    a["regs"] = order_regs(set(a["regs"]) | set(b["regs"]))
    # focus: union, keep first-seen order
    for f in b["f"]:
        if f not in a["f"]:
            a["f"].append(f)
    a["a"] = [min(a["a"][0], b["a"][0]), max(a["a"][1], b["a"][1])]
    # price: prefer a non-null, lower-of-the-two
    prices = [p for p in (a.get("price"), b.get("price")) if p is not None]
    a["price"] = min(prices) if prices else None
    # trial: any true wins, else any false, else null
    trials = [a.get("trial"), b.get("trial")]
    a["trial"] = True if True in trials else (False if False in trials else None)
    # rev: keep the most informative (longest)
    if len(b.get("rev", "")) > len(a.get("rev", "")):
        a["rev"] = b["rev"]; a["n"] = b["n"]
    # display name: keep the longer/more complete
    if len(b.get("prov", "")) > len(a.get("prov", "")):
        a["prov"] = b["prov"]
    return a


def main():
    by_key = {}
    raw_files = sorted(glob.glob(os.path.join(HERE, "raw_*.json")))
    total_in = 0
    for fp in raw_files:
        with open(fp) as fh:
            items = json.load(fh)
        for it in items:
            total_in += 1
            it["regs"] = order_regs(it.get("regs") or ["Central"])
            it["a"] = [max(3, it["a"][0]), min(9, it["a"][1])]
            k = norm_key(it["prov"])
            if k in by_key:
                merge(by_key[k], it)
            else:
                by_key[k] = it

    # attach official website + phone from contacts.json (matched by exact prov)
    contacts = {}
    cpath = os.path.join(HERE, "contacts.json")
    if os.path.exists(cpath):
        with open(cpath) as fh:
            for c in json.load(fh):
                contacts[c["prov"]] = c
    n_url = 0
    for it in by_key.values():
        ct = contacts.get(it["prov"], {})
        it["url"] = ct.get("url")
        it["phone"] = ct.get("phone")
        if it["url"]:
            n_url += 1

    classes = sorted(by_key.values(), key=lambda c: c["prov"].lower())
    print(f"contacts: {n_url}/{len(classes)} have a website")
    out = {
        "generated": datetime.date.today().isoformat(),
        "count": len(classes),
        "note": "Real Singapore enrichment providers, researched. Prices are typical monthly estimates and change often — confirm with the centre.",
        "classes": classes,
    }
    out_path = os.path.join(os.path.dirname(HERE), "classes.json")
    with open(out_path, "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"raw entries: {total_in}  ->  unique centres: {len(classes)}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()

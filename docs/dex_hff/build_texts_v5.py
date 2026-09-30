"""Builds per-country title/abstract shards for the Country Profile
"click a study, read it" feature.

The full title+abstract text for the analysis population is ~94MB — too
large to bundle upfront. Instead each country with >=1 geo-tagged study gets
its own small JSON shard, fetched lazily by the client only when a study
point in that country is clicked.

Inputs:
  docs/dex_hff/hsf_extraction_29sept_v5.csv   (title, abstract, record_id; v5 copy of build_texts.py)
  docs/data/studies.json                            (id[] gives record_id per study index s)
  docs/data/geo.json                                (s,c pairs -> which studies belong to which country)
  docs/data/countries.json                           (iso3 per country index c)

Output:
  docs/data/texts/<ISO3>.json  ->  {"s": [study indices...], "title": [...], "abstract": [...]}

Run: python docs/dex_hff/build_texts_v5.py  (after build_data_v5.py)
"""
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # docs/
DEX = ROOT / "dex_hff"
DATA = ROOT / "data"
OUT = DATA / "texts"
OUT.mkdir(exist_ok=True)

studies = json.loads((DATA / "studies.json").read_text(encoding="utf-8"))
geo = json.loads((DATA / "geo.json").read_text(encoding="utf-8"))
countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))

ids = studies["id"]  # position s -> record_id, same row order build_data.py wrote

raw = pd.read_csv(DEX / "hsf_extraction_29sept_v5.csv",
                   usecols=["record_id", "title", "abstract"])
title_of = dict(zip(raw["record_id"], raw["title"]))
abstract_of = dict(zip(raw["record_id"], raw["abstract"]))


def clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return str(v).strip()


studies_by_country = defaultdict(set)
for s, c in zip(geo["s"], geo["c"]):
    studies_by_country[c].add(s)

n_written = 0
for c, row in enumerate(countries):
    s_set = studies_by_country.get(c)
    if not s_set:
        continue
    s_sorted = sorted(s_set)
    payload = {
        "s": s_sorted,
        "title": [clean(title_of.get(ids[s])) for s in s_sorted],
        "abstract": [clean(abstract_of.get(ids[s])) for s in s_sorted],
    }
    path = OUT / f"{row['iso3']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    n_written += 1

print(f"wrote {n_written} country text shards to {OUT}")
sizes = sorted(((p.stat().st_size, p.name) for p in OUT.glob("*.json")), reverse=True)[:8]
for size, name in sizes:
    print(f"  {name}: {size / 1e6:.2f} MB")

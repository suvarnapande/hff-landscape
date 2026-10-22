"""Builds docs/data/text/ — the title and abstract of every study, for the Explorer's
"Download filtered studies (CSV)" button.

The per-country files in docs/data/texts/ only cover studies that name a country, so the
download needs its own copy covering all of them. The text (~90 MB) is split into chunks of
2,000 studies in site index order; the client fetches only the chunks the selected studies
fall in, and only when someone clicks the download button.

Titles and abstracts are taken as they are in the analysis master: whitespace is collapsed,
nothing else is changed (unlike texts/ and study_meta.json, "LMIC" is not reworded).

Inputs:
  docs/dex_hff/v2_5_1/hff_analysis_dataset_v2_5_1_included.csv   (record_id, title, abstract)
  docs/data/studies.json                                          (id[] gives record_id per study index s)

Output:
  docs/data/text/index.json  -> {"n": studies, "chunk": 2000, "files": ["000.json", ...], "source": ...}
  docs/data/text/NNN.json    -> {"start": first study index, "t": [titles...], "a": [abstracts...]}
                                "" where the master has no text.

Run: python scripts/build_study_text.py  (after build_data_v2_5.py; rerun when the master or
studies.json changes)
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent / "docs"  # docs/
DEX = ROOT / "dex_hff"
DATA = ROOT / "data"
OUT = DATA / "text"
MASTER = DEX / "v2_5_1" / "hff_analysis_dataset_v2_5_1_included.csv"
SOURCE_NAME = "HFF dataset v2.5.1"
CHUNK = 2000

studies = json.loads((DATA / "studies.json").read_text(encoding="utf-8"))
ids = studies["id"]  # position s -> record_id

raw = pd.read_csv(MASTER, low_memory=False, usecols=["record_id", "title", "abstract"])
if raw["record_id"].duplicated().any():
    sys.exit(f"ERROR: duplicate record_id in {MASTER.name}")
raw = raw.set_index("record_id")

missing = [rid for rid in ids if rid not in raw.index]
if missing:
    sys.exit(f"ERROR: {len(missing):,} site studies are not in {MASTER.name}, e.g. {missing[:5]}")


def clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v)).strip()


titles = [clean(raw.at[rid, "title"]) for rid in ids]
abstracts = [clean(raw.at[rid, "abstract"]) for rid in ids]

OUT.mkdir(exist_ok=True)
files = []
for start in range(0, len(ids), CHUNK):
    name = f"{start // CHUNK:03d}.json"
    chunk = {"start": start, "t": titles[start:start + CHUNK], "a": abstracts[start:start + CHUNK]}
    (OUT / name).write_text(json.dumps(chunk, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    files.append(name)

index = {"n": len(ids), "chunk": CHUNK, "files": files, "source": SOURCE_NAME}
(OUT / "index.json").write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")

size = sum(p.stat().st_size for p in OUT.glob("*.json"))
print(f"Wrote {OUT} ({len(files)} chunks + index.json, {size / 1e6:.1f} MB) for {len(ids):,} studies")
print(f"  without a title: {sum(1 for t in titles if not t):,}")
print(f"  without an abstract: {sum(1 for a in abstracts if not a):,}")

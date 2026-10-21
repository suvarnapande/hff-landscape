"""Builds docs/data/study_meta.json — bibliographic details for the Explorer's
"Download filtered studies (CSV)" button.

studies.json only holds coded fields, so the CSV needs titles, authors, journal
and DOI from the raw extraction. They're kept in their own file (~9MB, much
smaller once the host gzips it) that the client fetches only when someone
clicks the download button.

Inputs:
  docs/dex_hff/hsf_extraction_29sept_v5.csv   (record_id, title, authors, journal, doi, url)
  docs/data/studies.json                      (id[] gives record_id per study index s)

Output:
  docs/data/study_meta.json -> {"source": ..., "title": [...], "authors": [...], "journal": [...],
                                "doi": [...], "url": [...]}, each list aligned to study index s;
                                "" where the extraction has nothing ("Could not find" etc.).
  url is only kept for studies without a DOI (otherwise the DOI link is used).

Run: python docs/dex_hff/build_study_meta_v5.py  (after build_data_v5.py)
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # docs/
DEX = ROOT / "dex_hff"
DATA = ROOT / "data"
SOURCE_NAME = "HFF dataset v2.4.1"

studies = json.loads((DATA / "studies.json").read_text(encoding="utf-8"))
raw = pd.read_csv(DEX / "v2_4_1" / "hff_v2_4_1_site.csv", low_memory=False,
                  usecols=["record_id", "title", "authors", "journal", "doi", "url"]).set_index("record_id")

MISSING = {"", "could not find", "nan", "none", "null", "n/a", "na", "unknown"}
MOJIBAKE = re.compile("[ÂÃâ][\u0080-¿ŒœŠšŸŽžƒˆ˜–—‘’‚“”„†‡•…‰‹›€™]")
n_fixed = 0


def clean(v):
    """Blank out placeholders and repair UTF-8 text that was decoded as cp1252 (e.g. 'â€™' -> '’')."""
    global n_fixed
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = re.sub(r"\s+", " ", str(v)).strip()
    if s.lower() in MISSING:
        return ""
    if MOJIBAKE.search(s):
        try:
            fixed = s.encode("cp1252").decode("utf-8")
            n_fixed += 1
            s = fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    # Site-wide wording: "LMIC"/"LMICs" is shown as "L&MICs" (same as build_texts_v5.py).
    return re.sub(r"\bLMICs?\b", "L&MICs", s)


out = {"source": SOURCE_NAME, "title": [], "authors": [], "journal": [], "doi": [], "url": []}
for rid in studies["id"]:
    r = raw.loc[rid]
    doi = clean(r["doi"])
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
    url = clean(r["url"])
    out["title"].append(clean(r["title"]))
    out["authors"].append(clean(r["authors"]))
    out["journal"].append(clean(r["journal"]))
    out["doi"].append(doi)
    out["url"].append("" if doi or not url.lower().startswith("http") else url)

path = DATA / "study_meta.json"
path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
n = len(studies["id"])
print(f"Wrote {path} ({path.stat().st_size / 1e6:.1f} MB) for {n:,} studies")
for k in ("title", "authors", "journal", "doi", "url"):
    print(f"  {k}: {sum(1 for v in out[k] if v):,} filled")
print(f"  text fields with repaired encoding: {n_fixed:,}")

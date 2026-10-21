"""Find landing URLs for the Decision 17 HTA studies in v2.5.1 that have neither DOI nor URL.

v2.5 re-included 49 self-described health technology assessments (Decision 17); 28 of them have
no DOI and no URL, so the site cannot link to them. This searches two free public APIs by title:

  1. OpenAlex works search (five results), as in search_urls_v2_4_1.py
  2. PubMed E-utilities (esearch on the title, esummary for the candidates); many of these are
     CADTH reports, which PubMed indexes as NCBI Bookshelf books

A candidate is accepted only if its normalized title has SequenceMatcher ratio >= .95 with the
study's title and its publication year is within one year (the search_urls_v2_4_1.py rule).
URL preference: OpenAlex primary landing page, other OpenAlex landing page, NCBI Bookshelf page,
PubMed record. Equal best scores for distinct works are 'ambiguous' and not accepted.
Responses are cached in v2_5_1/url_search_hta/cache. No dataset edits: make_v2_5_csv.py reads the
accepted URLs from v2_5_1/url_search_hta/hta_url_results.csv.

Run: python scripts/search_urls_hta_v2_5_1.py
"""
import difflib
import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

DEX = Path(__file__).resolve().parent.parent / "docs" / "dex_hff"
DATA = DEX / "v2_5_1" / "hff_analysis_dataset_v2_5_1_included.csv"
OUT = DEX / "v2_5_1" / "url_search_hta"
CACHE = OUT / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
MISSING = {"", "na", "could not find", "none", "nan"}
UA = {"User-Agent": "HFF-URL-evidence-search/1.0"}


def missing(v):
    return str(v).strip().lower() in MISSING


def normalize(v):
    v = html.unescape(re.sub(r"<[^>]*>", " ", str(v))).lower()
    v = "".join(c if not unicodedata.category(c).startswith("P") else " " for c in v)
    return " ".join(v.split())


def get_json(url):
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    path = CACHE / (key + ".json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    for attempt in range(4):
        try:
            time.sleep(0.4)
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                body = json.loads(r.read().decode("utf-8"))
            path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            return body
        except Exception as exc:  # retried, then reported as an error row
            err = str(exc)
            time.sleep(2 * (attempt + 1))
    return {"error": err}


def openalex(title):
    q = title.replace("?", " ").replace("*", " ")
    body = get_json("https://api.openalex.org/works?" + urllib.parse.urlencode({"search": q, "per-page": 5}))
    if "error" in body:
        return None, body["error"]
    out = []
    for w in body.get("results", []):
        urls = [(w.get("primary_location") or {}).get("landing_page_url")]
        urls += [loc.get("landing_page_url") for loc in w.get("locations") or []]
        urls = [u for u in urls if u]
        ids = w.get("ids") or {}
        if not urls and ids.get("pmid"):
            urls = [ids["pmid"]]
        out.append({"title": w.get("display_name") or "", "year": w.get("publication_year"),
                    "id": w.get("id"), "url": urls[0] if urls else "", "source": "openalex",
                    "doi": w.get("doi") or ""})
    return out, ""


def pubmed(title):
    term = re.sub(r"[\[\]():;\"]", " ", title)
    body = get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": term + "[Title]", "retmode": "json", "retmax": 5}))
    if "error" in body:
        return None, body["error"]
    ids = body.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return [], ""
    summ = get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}))
    if "error" in summ:
        return None, summ["error"]
    out = []
    for pmid in ids:
        r = summ.get("result", {}).get(pmid, {})
        if not r:
            continue
        year = re.match(r"\d{4}", r.get("pubdate") or r.get("sortpubdate") or "")
        book = r.get("bookname") or ""
        aids = {a.get("idtype"): a.get("value") for a in r.get("articleids", [])}
        url = (f"https://www.ncbi.nlm.nih.gov/books/{aids['bookaccession']}/" if aids.get("bookaccession")
               else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
        out.append({"title": r.get("title") or book, "year": int(year.group()) if year else None,
                    "id": "PMID:" + pmid, "url": url,
                    "source": "ncbi_bookshelf" if aids.get("bookaccession") else "pubmed", "doi": aids.get("doi", "")})
    return out, ""


df = pd.read_csv(DATA, dtype=str, keep_default_na=False)
todo = df[(df["function_label_source"] == "hta_rule_decision17") & df["doi"].map(missing) & df["url"].map(missing)]
print(f"{len(todo)} Decision 17 HTA studies without DOI or URL")

rows = []
for _, s in todo.iterrows():
    n_title, year = normalize(s["title"]), int(s["year"]) if s["year"].isdigit() else None
    cands, errors = [], []
    for fn in (openalex, pubmed):
        found, err = fn(s["title"])
        if err:
            errors.append(f"{fn.__name__}: {err}")
        cands += found or []
    for c in cands:
        c["similarity"] = difflib.SequenceMatcher(None, n_title, normalize(c["title"])).ratio()
    good = [c for c in cands if c["similarity"] >= .95 and c["url"]]
    year_ok = [c for c in good if year is None or c["year"] is None or abs(c["year"] - year) <= 1]
    rank = {"openalex": 0, "ncbi_bookshelf": 1, "pubmed": 2}
    best = max(cands, key=lambda c: c["similarity"]) if cands else None
    if year_ok:
        top = max(c["similarity"] for c in year_ok)
        tied = {normalize(c["title"]) + str(c["year"]) for c in year_ok if c["similarity"] == top}
        pick = sorted([c for c in year_ok if c["similarity"] == top], key=lambda c: rank[c["source"]])[0]
        decision = "accepted" if len(tied) == 1 else "ambiguous"
    else:
        pick = best
        decision = ("error" if errors and not cands else "no_match" if not cands
                    else "year_mismatch" if good else "below_threshold")
    rows.append({"record_id": s["record_id"], "title": s["title"], "year": s["year"],
                 "match_title": pick["title"] if pick else "", "match_year": pick["year"] if pick else "",
                 "similarity": round(pick["similarity"], 4) if pick else "", "match_id": pick["id"] if pick else "",
                 "url": pick["url"] if pick and decision == "accepted" else "",
                 "url_source": pick["source"] if pick and decision == "accepted" else "",
                 "found_doi": pick["doi"] if pick else "", "decision": decision, "errors": "; ".join(errors)})

res = pd.DataFrame(rows)
res.to_csv(OUT / "hta_url_results.csv", index=False, encoding="utf-8")
print(res["decision"].value_counts().to_dict())
print(res.loc[res["decision"] == "accepted", "url_source"].value_counts().to_dict())
print("wrote", OUT / "hta_url_results.csv")

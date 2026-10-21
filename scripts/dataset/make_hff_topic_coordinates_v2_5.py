#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_hff_topic_coordinates_v2_5.py -- topic-map coordinates for all 53,414 HFF v2.5 included studies.

    python -X utf8 projects/hff/final_includes/make_hff_topic_coordinates_v2_5.py [--replace]

Local only (no API calls; the sentence-embedding model runs on this machine).

v2.4's coordinates (make_hff_topic_coordinates_v2_4.py) cover 53,365 studies: the refitted topic
model (projects/hsf/analysis/R/05-topic-model_v3.py) was fitted on the v2.3 included set. v2.5 adds
49 records re-included by Decision 17 (self-described HTAs), which were not in that fit. They are
PLACED into the existing map, not refitted (L. Sempe, 2026-10-14), so no fitted point moves and no
cluster changes:
  1. embed title + ". " + abstract with the same model (all-MiniLM-L6-v2) the fit used;
  2. find the k = 15 nearest fitted studies by cosine similarity, among the 53,365 v2.4 included
     studies (the 417 duplicate_doi rows of the fit are not used as neighbours);
  3. x, y = the median of the neighbours' coordinates; cluster = the most common cluster among the
     neighbours (ties: the nearer neighbour's cluster).
Writes projects/hff/final_includes/hff_topic_coordinates_v2_5.csv (53,414 rows):
  record_id, x, y, topic_cluster_id, topic_cluster_label,
  topic_placement   "fitted" (53,365) | "nearest-neighbour, k=15" (49)
and copies it into projects/hff/hff_export/ and projects/hff/hff_share_v2_5/.
"""
from __future__ import annotations

import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FI = ROOT / "projects/hff/final_includes"
TM = ROOT / "projects/hsf/analysis/data"
ADS = FI / "hff_analysis_dataset_v2_5.parquet"
OUT = FI / "hff_topic_coordinates_v2_5.csv"
K = 15
PLACED = f"nearest-neighbour, k={K}"


def main() -> None:
    if OUT.exists() and "--replace" not in sys.argv:
        raise SystemExit(f"{OUT.name} exists; pass --replace")
    c4 = pd.read_csv(FI / "hff_topic_coordinates_v2_4.csv", dtype={"record_id": str, "topic_cluster_id": str})
    m = pd.read_csv(TM / "topic_map_v3.csv", dtype={"record_id": str})
    emb = np.load(TM / "topic_embeddings_v3.npy")
    assert len(emb) == len(m)
    lab = pd.read_csv(TM / "topic_labels_v3.csv")
    label = dict(zip(lab["cluster"].astype(str), lab["label"]))
    label["-1"] = "Unclustered (noise)"

    d = pd.read_parquet(ADS, columns=["record_id", "title", "abstract", "analysis_include"])
    d["record_id"] = d["record_id"].astype(str)
    inc = d[d["analysis_include"]]
    new = inc[~inc["record_id"].isin(set(c4["record_id"]))]
    assert len(inc) == 53414 and len(new) == 49, (len(inc), len(new))

    keep = m["record_id"].isin(set(c4["record_id"])).values           # the 53,365 fitted, still included
    E = emb[keep]
    E = E / np.linalg.norm(E, axis=1, keepdims=True)
    fit = m[keep].reset_index(drop=True)

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = (new["title"].fillna("") + ". " + new["abstract"].fillna("")).str.strip().tolist()
    q = model.encode(texts, convert_to_numpy=True)
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    sims = q @ E.T
    rows = []
    for i, rid in enumerate(new["record_id"]):
        nn = np.argsort(-sims[i])[:K]
        cl = [str(int(fit.at[j, "cluster"])) for j in nn]
        cnt = Counter(cl)
        top = max(cnt.values())
        cluster = next(c for c in cl if cnt[c] == top)                  # tie -> nearer neighbour
        rows.append({"record_id": rid, "x": round(float(np.median(fit.loc[nn, "x"])), 4),
                     "y": round(float(np.median(fit.loc[nn, "y"])), 4), "topic_cluster_id": cluster,
                     "topic_cluster_label": label[cluster], "topic_placement": PLACED,
                     "_nn_share": top / K, "_max_sim": float(sims[i, nn[0]])})
    p = pd.DataFrame(rows)
    out = pd.concat([c4.assign(topic_placement="fitted"), p.drop(columns=["_nn_share", "_max_sim"])], ignore_index=True)
    assert len(out) == 53414 and out["record_id"].is_unique and set(out["record_id"]) == set(inc["record_id"])
    out.to_csv(OUT, index=False, encoding="utf-8")
    for dest in (ROOT / "projects/hff/hff_export", ROOT / "projects/hff/hff_share_v2_5"):
        shutil.copy2(OUT, dest / OUT.name)
    print(f"wrote {OUT.name}: {len(out):,} ({(out.topic_placement == 'fitted').sum():,} fitted, {len(p)} placed); "
          f"placed clusters: {p['topic_cluster_id'].value_counts().head(6).to_dict()}; "
          f"neighbour agreement median {p['_nn_share'].median():.2f}; nearest similarity median {p['_max_sim'].median():.2f}")


if __name__ == "__main__":
    main()

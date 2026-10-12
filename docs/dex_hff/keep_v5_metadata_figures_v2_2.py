"""Keeps the v5 versions of the figures built on bibliographic metadata, after the v2.2 rebuild.

The v2.2 dataset has no DOI, authors, affiliations, funders, open-access flag, MeSH/OpenAlex
topics or topic clusters for the 20,795 studies added after v1 (V2_2_DATASET_README.md, "Known
limitations"). Until that metadata exists, the figures that depend on it stay as they were built
from the HSF extraction 29 Sept v5 (36,495 studies), and their captions say so.

For every file in KEEP_V5 this script:
  - restores the image from V5_COMMIT (the last v5 build on the site)
  - restores its gallery title/caption from that commit's content.json, plus a note
and it restores the "Open access & author countries" gallery section, which only
build_open_access_v5.py writes.

Run LAST, after build_figures_v2_2.py and build_fcas_outcomes_v2_2.py:
    python docs/dex_hff/keep_v5_metadata_figures_v2_2.py
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # docs/
REPO = ROOT.parent
DATA = ROOT / "data"
FIGS = ROOT / "figures"
V5_COMMIT = "f59156c"

V5_NOTE = ("Note: this figure is still built from the HSF extraction 29 Sept v5 (36,495 studies). "
           "It needs bibliographic metadata (authors, funders, DOI, MeSH or topic clusters), which is "
           "not yet available for the studies added in the v2.2 dataset.")

KEEP_V5 = [
    # Topic clusters (topic model, OpenAlex topics)
    "fig_theme_rank.png", "fig_topicmap.png", "fig_topicmap_income.png",
    "fig_topic_landscape.png", "fig_topic_landscape_treemap.png", "fig_topic_clusters.png",
    # Disease focus (MeSH)
    "fig_disease_circular.png", "fig_disease_method.png", "fig_funder_opportunity.png",
    "fig_transition.png", "fig_funder_trajectory.png", "fig_map_disease.png",
    # Geographic inequalities: one of its two panels is "has a local author"
    "fig_forest.png",
    # Research ownership & collaboration (author affiliations)
    "fig_map_authorship.png", "fig_authorship_pattern.png", "fig_authorship_by_function.png",
    "fig_authorship_outcome_heatmap.png", "fig_collab_chord.png", "fig_funder_capacity.png",
    # Research funding (CrossRef funders); fig_funder_types_v5.png is not rebuilt at all
    "fig_funder_types_v5.png", "fig_funder_funders_treemap.png", "fig_funder_function_heatmap.png",
    "fig_funder_outcome_heatmap.png", "fig_funder_trend.png", "fig_funder_authorship_alluvial.png",
    # hidden, but still built from funders
    "fig_funder_funders.png", "fig_funder_function_bubbles.png", "fig_funder_function_mix.png",
    # Open access & author countries (not rebuilt at all)
    "fig_map_oa_author_v5.png", "fig_oa_trend_v5.png", "fig_oa_author_income_v5.png",
    "fig_oa_author_countries_v5.png",
]
OA_SECTION = "Open access & author countries"


def git_show(path):
    return subprocess.run(["git", "show", f"{V5_COMMIT}:{path}"], cwd=REPO,
                          capture_output=True, check=True).stdout


for name in KEEP_V5:
    (FIGS / name).write_bytes(git_show(f"docs/figures/{name}"))
print(f"Restored {len(KEEP_V5)} figures from {V5_COMMIT}")

old = json.loads(git_show("docs/data/content.json").decode("utf-8"))
old_entry = {f["file"]: f for g in old["gallery"] for f in g["figs"]}
content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))


def with_note(entry):
    entry = dict(entry)
    entry["caption"] = entry["caption"].rstrip() + " " + V5_NOTE
    return entry


n_captions = 0
for section in content["gallery"]:
    for i, f in enumerate(section["figs"]):
        if f["file"] in KEEP_V5:
            section["figs"][i] = with_note(old_entry[f["file"]])
            n_captions += 1

if not any(g["title"] == OA_SECTION for g in content["gallery"]):
    oa = next(g for g in old["gallery"] if g["title"] == OA_SECTION)
    oa = dict(oa, figs=[with_note(f) for f in oa["figs"]])
    content["gallery"].append(oa)
    n_captions += len(oa["figs"])

(DATA / "content.json").write_text(json.dumps(content, allow_nan=False, ensure_ascii=False), encoding="utf-8")
print(f"Restored {n_captions} gallery captions (with the v5 note) in content.json")

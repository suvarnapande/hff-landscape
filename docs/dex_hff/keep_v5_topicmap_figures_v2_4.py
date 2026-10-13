"""Keeps the v5 versions of the two topic-map figures after the v2.4 rebuild.

v2.4 refitted the topic clusters for every study but does not include the new model's 2-D map
positions; topic_map.csv holds only the old model's positions, for the v1 studies, numbered with
the old clusters. So fig_topicmap.png and fig_topicmap_income.png cannot be drawn for v2.4 and
stay as built from the HSF extraction 29 Sept v5, with a note in their captions. Every other
figure, including the "Top 20 research themes" ranking, is built from v2.4.1.

To retire this script: get the v2.4 model's per-study coordinates (record_id, x, y, cluster) from
the dataset team, replace topic_map.csv with them, and drop this step from the build.

Run LAST, after build_figures_v2_4.py, build_funder_types_v2_4.py, build_fcas_outcomes_v2_4.py
and build_open_access_v2_4.py:
    python docs/dex_hff/keep_v5_topicmap_figures_v2_4.py
"""
import sys
sys.exit("Retired: build_figures_v2_4.py now draws both topic maps from "
         "v2_4 from Lucas/hff_topic_coordinates_v2_4.csv. Do not run this script.")

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # docs/
REPO = ROOT.parent
DATA = ROOT / "data"
FIGS = ROOT / "figures"
V5_COMMIT = "f59156c"  # the last v5 build on the site
KEEP_V5 = ["fig_topicmap.png", "fig_topicmap_income.png"]
V5_NOTE = ("Note: this map is still the version built from the HSF extraction 29 Sept v5 (36,495 studies). "
           "The v2.4 dataset refitted the topic clusters for all studies but does not yet include the "
           "coordinates needed to redraw the map.")


def git_show(path):
    return subprocess.run(["git", "show", f"{V5_COMMIT}:{path}"], cwd=REPO,
                          capture_output=True, check=True).stdout


for name in KEEP_V5:
    (FIGS / name).write_bytes(git_show(f"docs/figures/{name}"))
old = json.loads(git_show("docs/data/content.json").decode("utf-8"))
old_entry = {f["file"]: f for g in old["gallery"] for f in g["figs"]}
content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
n = 0
for section in content["gallery"]:
    for i, f in enumerate(section["figs"]):
        if f["file"] in KEEP_V5:
            entry = dict(old_entry[f["file"]])
            entry["caption"] = entry["caption"].rstrip() + " " + V5_NOTE
            section["figs"][i] = entry
            n += 1
(DATA / "content.json").write_text(json.dumps(content, allow_nan=False, ensure_ascii=False), encoding="utf-8")
print(f"Kept {len(KEEP_V5)} topic-map figures at v5; {n} gallery captions noted")

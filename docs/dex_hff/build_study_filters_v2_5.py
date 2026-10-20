"""Builds docs/data/study_filters.json — funder and publication language per study, for the
Explorer's "Funder" and "Publication language" filters.

Standalone like build_study_meta_v2_5.py: it reads studies.json for the study order and
doesn't touch any other output, so it can run without a full rebuild.

Funder names use the same grouping as fig_funder_funders (build_figures_v2_5.py):
_norm_funder_key() merges case/punctuation/"&" variants and FUNDER_ALIASES folds in
abbreviations; each group is shown under its most common raw spelling. A study naming
several funders is listed under each.

Language is the CrossRef language code. "Could not find" (no DOI or no CrossRef language)
becomes "Not recorded". "ng" is not a real language tag here: all those records are
English-language IGI Global titles, so they count as English.

Inputs:
  docs/dex_hff/v2_5_1/hff_v2_5_1_site.csv   (record_id, research_funder, language)
  docs/data/studies.json                    (id[] gives record_id per study index s)

Output:
  docs/data/study_filters.json -> {"source", "funders": [name], "funder_n": [studies],
                                   "funder": [[funder index, ...] per study],
                                   "languages": [name], "language_n": [studies],
                                   "language": [language index per study]}
  funders and languages are sorted by study count (most first); "Not recorded" goes last.

Run: python docs/dex_hff/build_study_filters_v2_5.py  (after build_data_v2_5.py)
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # docs/
DEX = ROOT / "dex_hff"
DATA = ROOT / "data"
SOURCE_NAME = "HFF dataset v2.5.1"

# Copied from build_figures_v2_5.py so the filter matches the top-funders figure.
FUNDER_ALIASES = {
    "nih": "National Institutes of Health",
    "gates foundation": "Bill and Melinda Gates Foundation",
    "who": "World Health Organization",
    "cdc": "Centers for Disease Control and Prevention",
    "nsf": "National Science Foundation",
    "dfid": "Department for International Development",
    "department for international development uk government": "Department for International Development",
    "usaid": "United States Agency for International Development",
    "world bank": "World Bank Group",
    "horizon 2020 framework programme": "Horizon 2020",
    "national social science foundation of china": "National Social Science Fund of China",
}

LANGUAGE_NAMES = {
    "en": "English", "ng": "English", "ko": "Korean", "de": "German", "fa": "Persian",
    "fr": "French", "es": "Spanish", "pt": "Portuguese", "ru": "Russian", "hu": "Hungarian",
    "no": "Norwegian", "pl": "Polish", "it": "Italian", "ja": "Japanese", "zh": "Chinese",
    "nl": "Dutch", "tr": "Turkish", "ar": "Arabic",
}
NOT_RECORDED = "Not recorded"

MOJIBAKE = re.compile("[ÂÃâ][\u0080-¿ŒœŠšŸŽžƒˆ˜–—‘’‚“”„†‡•…‰‹›€™]")


def _norm_funder_key(s):
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[.,\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.startswith("the "):
        s = s[4:]
    return s


def fix_text(s):
    """Repair UTF-8 text that was decoded as cp1252 (same rule as build_study_meta_v2_5.py)."""
    s = re.sub(r"\s+", " ", s).strip()
    if MOJIBAKE.search(s):
        try:
            return s.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return s


studies = json.loads((DATA / "studies.json").read_text(encoding="utf-8"))
raw = pd.read_csv(DEX / "v2_5_1" / "hff_v2_5_1_site.csv", low_memory=False,
                  usecols=["record_id", "research_funder", "language"]).set_index("record_id")
rows = raw.loc[studies["id"]]

# --- funders ---
raw_spellings = defaultdict(Counter)
keys_of_s = []
for fn in rows["research_funder"]:
    keys = set()
    if isinstance(fn, str) and fn.strip() and fn != "Could not find":
        for t in {fix_text(t) for t in fn.split(";")}:
            if not t:
                continue
            key = _norm_funder_key(t)
            if key in FUNDER_ALIASES:
                key = _norm_funder_key(FUNDER_ALIASES[key])
            raw_spellings[key][t] += 1
            keys.add(key)
    keys_of_s.append(keys)

display = {key: ctr.most_common(1)[0][0] for key, ctr in raw_spellings.items()}
for alias_to in FUNDER_ALIASES.values():
    if _norm_funder_key(alias_to) in display:
        display[_norm_funder_key(alias_to)] = alias_to
n_of_key = Counter(k for keys in keys_of_s for k in keys)
order = sorted(n_of_key, key=lambda k: (-n_of_key[k], display[k].lower()))
idx_of_key = {k: i for i, k in enumerate(order)}

# --- languages ---
lang_names = []
for code in rows["language"]:
    code = str(code).strip().lower() if isinstance(code, str) else ""
    lang_names.append(LANGUAGE_NAMES.get(code, code.upper() if code and code != "could not find" else NOT_RECORDED))
n_of_lang = Counter(lang_names)
lang_order = sorted(n_of_lang, key=lambda l: (l == NOT_RECORDED, -n_of_lang[l], l))
idx_of_lang = {l: i for i, l in enumerate(lang_order)}

out = {
    "source": SOURCE_NAME,
    "funders": [display[k] for k in order],
    "funder_n": [n_of_key[k] for k in order],
    "funder": [sorted(idx_of_key[k] for k in keys) for keys in keys_of_s],
    "languages": lang_order,
    "language_n": [n_of_lang[l] for l in lang_order],
    "language": [idx_of_lang[l] for l in lang_names],
}

path = DATA / "study_filters.json"
path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
n = len(studies["id"])
n_funded = sum(1 for keys in keys_of_s if keys)
print(f"Wrote {path} ({path.stat().st_size / 1e6:.1f} MB) for {n:,} studies")
print(f"  studies naming a funder: {n_funded:,} ({100 * n_funded / n:.1f}%); distinct funders: {len(order):,}")
print("  top funders:", ", ".join(f"{display[k]} ({n_of_key[k]:,})" for k in order[:5]))
print("  languages:", ", ".join(f"{l} ({n_of_lang[l]:,})" for l in lang_order))

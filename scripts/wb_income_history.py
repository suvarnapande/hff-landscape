"""World Bank income group of a country in a study's publication year.

Reads the World Bank's historical classification (OGHIST, "Country Analytical History" sheet).
Every docs/dex_hff/OGHIST*.xlsx is read and the one reaching the latest fiscal year is used, so
saving a newer download next to the old one is enough. Source and licence (CC BY 4.0):
https://datacatalog.worldbank.org/search/dataset/0037712 (World Bank Country and Lending Groups).

Convention (same as build_data_v2_5.py): a study published in calendar year Y takes the group of
fiscal year Y+1, which the World Bank publishes in July of Y. This matches the dataset's own
publication-year field for 97.9% of single-country studies. Where the file has no value for that
fiscal year (the latest publications, or an economy not classified that year), the current
group passed in by the caller is used.

    from wb_income_history import WB_HISTORY, pub_year_group
    pub_year_group("KEN", 2014, current="Lower middle income")
"""
from pathlib import Path

import pandas as pd

DEX = Path(__file__).resolve().parent.parent / "docs" / "dex_hff"
GROUP = {"L": "Low income", "LM": "Lower middle income", "UM": "Upper middle income", "H": "High income"}


def _read(path):
    raw = pd.read_excel(path, sheet_name="Country Analytical History", header=None)
    fy_row = next(i for i in range(12) if any(str(v).startswith("FY") for v in raw.iloc[i]))
    fy_col = {j: (2000 if int(str(v)[2:4]) < 80 else 1900) + int(str(v)[2:4])
              for j, v in enumerate(raw.iloc[fy_row]) if str(v).startswith("FY")}
    out, names = {}, {}
    for _, row in raw.iloc[fy_row + 1:].iterrows():
        if isinstance(row[0], str) and len(row[0]) == 3:
            names[row[0]] = str(row[1]).strip()
            for j, fy in fy_col.items():
                g = GROUP.get(str(row[j]).strip())
                if g:
                    out[(row[0], fy)] = g
    return out, names, max(fy_col.values())


def _load():
    best = None
    for path in sorted(DEX.glob("OGHIST*.xlsx")):
        table, names, last_fy = _read(path)
        if best is None or last_fy > best[3]:
            best = (table, names, path, last_fy)
    if best is None:
        raise FileNotFoundError(f"no OGHIST*.xlsx in {DEX}")
    return best


WB_HISTORY, WB_NAMES, WB_HISTORY_FILE, WB_LAST_FY = _load()  # WB_NAMES: iso3 -> World Bank economy name


def pub_year_group(iso3, year, current=None):
    """Group of fiscal year year+1, else `current`."""
    return WB_HISTORY.get((iso3, int(year) + 1), current)

"""One-off: HSF extraction 29 Sept v5.xlsx (Data sheet) -> hsf_extraction_29sept_v5.csv,
so the *_v5 build scripts can read it quickly (and repeatedly, with usecols).

Run: python docs/dex_hff/make_v5_csv.py
"""
from pathlib import Path

import pandas as pd

DEX = Path(__file__).resolve().parent
src = DEX / "HSF extraction 29 Sept v5.xlsx"
dst = DEX / "hsf_extraction_29sept_v5.csv"
df = pd.read_excel(src, sheet_name="Data", dtype=str)
df.to_csv(dst, index=False, encoding="utf-8")
print(f"wrote {dst.name}: {len(df):,} rows x {len(df.columns)} cols")

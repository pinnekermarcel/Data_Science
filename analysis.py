#!/usr/bin/env python3
"""Load your slice and print lines, orders and customers. Your analysis goes below.

    python3 analysis.py

Set TERRITORY and CATEGORY to your slice (group mail, or your row of slices.csv).
Reads your extract AWC/awc_flat.csv.
"""
from pathlib import Path

import pandas as pd

# ── set these two to YOUR slice ──────────────────────────────────────────────
TERRITORY = "<e.g. Northwest>"
CATEGORY = "<e.g. Bikes>"
# ─────────────────────────────────────────────────────────────────────────────


def find_extract():
    """AWC/awc_flat.csv, wherever the repository sits relative to this file."""
    here = Path(__file__).resolve()
    for base in [here.parent] + list(here.parents):
        c = base / "AWC" / "awc_flat.csv"
        if c.exists():
            return c
    raise SystemExit("AWC/awc_flat.csv not found -- run this inside the course "
                     "material, or edit the path below.")


def load():
    f = pd.read_csv(find_extract())
    d = f[(f.TerritoryName == TERRITORY) & (f.Category == CATEGORY)].copy()
    if d.empty:
        raise SystemExit(f"no rows for {TERRITORY!r} / {CATEGORY!r} -- check "
                         f"the spelling against slices.csv")
    d["OrderDate"] = pd.to_datetime(d.OrderDate)
    # one row per order line, in a fixed order
    return d.sort_values("SalesOrderDetailID").reset_index(drop=True)


if __name__ == "__main__":
    d = load()
    print(f"slice: {TERRITORY} / {CATEGORY}")
    print(f"  lines:     {len(d):,}")
    print(f"  orders:    {d.SalesOrderID.nunique():,}")
    print(f"  customers: {d.CustomerID.nunique():,}")
    print("\nPut those three into manifest.yaml -> findings.")
    print("The rest of the findings block is yours to compute.")

    # ── your analysis from here ──────────────────────────────────────────────

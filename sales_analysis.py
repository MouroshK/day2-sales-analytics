import csv
import math
from pathlib import Path

# Use Path for clean cross-platform path handling
DATA_PATH = Path("data") / "electronics_sales.csv"


def read_sales(path: Path = DATA_PATH) -> list[dict[str, str]]:
    """Read the CSV using csv.DictReader and return a list of row dicts."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        column_names = reader.fieldnames or []
        rows = [row for row in reader]

    print(f"Rows read: {len(rows)}")
    print(f"Columns: {', '.join(column_names)}")
    return rows


def parse_number(value: str) -> float | None:
    """Convert a messy numeric string to a float, or return None if untrustworthy."""
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return None

    # Strip prefixes
    for prefix in ["KES", "Ksh", "ksh", "kes", "$"]:
        if cleaned.upper().startswith(prefix.upper()):
            cleaned = cleaned[len(prefix):].strip()

    # Strip commas
    cleaned = cleaned.replace(",", "").strip()

    try:
        val = float(cleaned)
        return val if not math.isnan(val) else None
    except ValueError:
        return None
    

def convert_rows(rows: list[dict[str, str]]) -> tuple[list[dict], list[dict]]:
    """
    Separates valid rows from untrustworthy rows.
    Calculates revenue = quantity * unit_price_kes for valid rows.
    """
    clean_rows: list[dict] = []
    skipped_rows: list[dict] = []

    for row in rows:
        raw_qty = row.get("quantity")
        raw_price = row.get("unit_price_kes")

        parsed_qty = parse_number(raw_qty)
        parsed_price = parse_number(raw_price)

        # Rule 1: Quantity must be valid
        if parsed_qty is None:
            skipped_rows.append({**row, "reason": f"invalid or missing quantity ('{raw_qty}')"})
            continue

        # Rule 2: Price must be valid
        if parsed_price is None:
            skipped_rows.append({**row, "reason": f"invalid or missing unit price ('{raw_price}')"})
            continue

        # Rule 3: Quantity must be a positive whole number
        if parsed_qty <= 0 or not parsed_qty.is_integer():
            skipped_rows.append({**row, "reason": f"non-positive or fractional quantity ('{raw_qty}')"})
            continue

        # Rule 4: Unit price must not be negative
        if parsed_price < 0:
            skipped_rows.append({**row, "reason": f"negative unit price ('{raw_price}')"})
            continue

        # Safe row: cast types and calculate transaction revenue
        clean_row = dict(row)
        clean_row["quantity"] = int(parsed_qty)
        clean_row["unit_price_kes"] = float(parsed_price)
        clean_row["revenue"] = clean_row["quantity"] * clean_row["unit_price_kes"]
        clean_rows.append(clean_row)

    return clean_rows, skipped_rows


def total_revenue(rows: list[dict]) -> float:
    """Sum total revenue across all clean rows."""
    return sum(row["revenue"] for row in rows)


def revenue_by(rows: list[dict], field: str) -> dict[str, float]:
    """Group and sum revenue by any column name using a standard dict."""
    totals: dict[str, float] = {}
    for row in rows:
        key = row.get(field, "Unknown")
        totals[key] = totals.get(key, 0.0) + row["revenue"]
    return totals


def top_n(totals: dict[str, float], n: int = 3) -> list[tuple[str, float]]:
    """
    Ranks items by value descending.
    Tie-breaking: Revenue descending (-item[1]), then alphabetical ascending (item[0]).
    """
    return sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:n]


def high_value(rows: list[dict], threshold: float) -> list[dict]:
    """Filter transactions whose revenue is at or above threshold."""
    return [row for row in rows if row["revenue"] >= threshold]


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("Cannot compute mean of empty list.")
    return sum(values) / len(values)

def median(values: list[float]) -> float:
    if not values:
        raise ValueError("Cannot compute median of empty list.")

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2

    if n % 2 == 1:
        return float(sorted_vals[mid])
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def minimum_maximum(values: list[float]) -> tuple[float, float]:
    if not values:
        raise ValueError("Cannot compute min/max of empty list.")

    cur_min = values[0]
    cur_max = values[0]

    for val in values[1:]:
        if val < cur_min:
            cur_min = val
        if val > cur_max:
            cur_max = val

    return cur_min, cur_max



def verify_with_pandas(path: Path, my_results: dict) -> None:
    """Recomputes headline metrics using pandas to verify accuracy."""
    try:
        import pandas as pd
    except ImportError:
        print("pandas not installed; skipping Task 8 verification.")
        return

    df = pd.read_csv(path)

    def clean_num(v):
        if pd.isna(v):
            return None
        s = str(v).strip()
        for pfx in ["KES", "Ksh", "ksh", "kes", "$"]:
            if s.upper().startswith(pfx.upper()):
                s = s[len(pfx):].strip()
        s = s.replace(",", "").strip()
        try:
            val = float(s)
            return val if not math.isnan(val) else None
        except ValueError:
            return None

    df["qty_clean"] = df["quantity"].apply(clean_num)
    df["price_clean"] = df["unit_price_kes"].apply(clean_num)

    valid_df = df[
        df["qty_clean"].notna()
        & df["price_clean"].notna()
        & (df["qty_clean"] > 0)
        & (df["qty_clean"] % 1 == 0)
        & (df["price_clean"] >= 0)
    ].copy()

    valid_df["quantity"] = valid_df["qty_clean"].astype(int)
    valid_df["unit_price_kes"] = valid_df["price_clean"].astype(float)
    valid_df["revenue"] = valid_df["quantity"] * valid_df["unit_price_kes"]

    pd_tot = float(valid_df["revenue"].sum())
    pd_by_prod = valid_df.groupby("product")["revenue"].sum().to_dict()
    pd_top3 = list(valid_df.groupby("product")["revenue"].sum().sort_values(ascending=False).head(3).items())
    pd_mean = float(valid_df["revenue"].mean())
    pd_median = float(valid_df["revenue"].median())

    tot_match = math.isclose(my_results["total_revenue"], pd_tot, abs_tol=1e-2)
    prod_match = all(math.isclose(my_results["prod_revenue"].get(k, 0.0), v, abs_tol=1e-2) for k, v in pd_by_prod.items())
    top3_match = (
        len(my_results["top_3"]) == len(pd_top3)
        and all(m[0] == p[0] and math.isclose(m[1], p[1], abs_tol=1e-2) for m, p in zip(my_results["top_3"], pd_top3))
    )
    mean_match = math.isclose(my_results["mean"], pd_mean, abs_tol=1e-2)
    med_match = math.isclose(my_results["median"], pd_median, abs_tol=1e-2)

    print("\n=== pandas verification ===")
    print(f"Total revenue      : {'MATCH' if tot_match else 'MISMATCH'}")
    print(f"Revenue by product : {'MATCH' if prod_match else 'MISMATCH'}")
    print(f"Top 3              : {'MATCH' if top3_match else 'MISMATCH'}")
    print(f"Mean / median      : {'MATCH' if (mean_match and med_match) else 'MISMATCH'}")


if __name__ == "__main__":
    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "sales_report.txt"

    # Ingest
    raw_rows = read_sales(DATA_PATH)
    clean_rows, skipped_rows = convert_rows(raw_rows)

    # Metrics
    tot_rev = total_revenue(clean_rows)
    prod_rev = revenue_by(clean_rows, "product")
    top_3_products = top_n(prod_rev, 3)

    THRESHOLD = 50000.0
    high_val = high_value(clean_rows, THRESHOLD)

    rev_vals = [r["revenue"] for r in clean_rows]
    mean_val = mean(rev_vals)
    med_val = median(rev_vals)
    min_val, max_val = minimum_maximum(rev_vals)

    # Format output matching expected_report.txt
    skipped_str = ", ".join(f"{s['sale_id']}: {s['reason']}" for s in skipped_rows)

    report_lines = [
        "=== Sales report: September 2026 ===",
        f"Rows read          : {len(raw_rows)}",
        f"Rows used          : {len(clean_rows)}",
        f"Rows skipped       : {len(skipped_rows)}   ({skipped_str})",
        "",
        f"Total revenue (KES): {tot_rev:,.2f}",
        "",
        "Revenue by product (KES)",
    ]

    for p, amt in sorted(prod_rev.items(), key=lambda x: -x[1]):
        report_lines.append(f"  {p:<24} {amt:>12,.2f}")

    report_lines.extend([
        "",
        "Top 3 products",
    ])
    for idx, (p, amt) in enumerate(top_3_products, start=1):
        report_lines.append(f"  {idx}. {p} - KES {amt:,.2f}")

    report_lines.extend([
        "",
        f"High-value transactions (>= KES {THRESHOLD:,.2f}): {len(high_val)}",
    ])
    for s in high_val:
        report_lines.append(
            f"  {s['sale_id']:<7} {s['sale_date']}  {s['store']:<18} {s['product']:<22} KES {s['revenue']:>10,.2f}"
        )

    report_lines.extend([
        "",
        "Transaction revenue statistics",
        f"  mean   : {mean_val:,.2f}",
        f"  median : {med_val:,.2f}",
        f"  min    : {min_val:,.2f}",
        f"  max    : {max_val:,.2f}",
    ])

    report_text = "\n".join(report_lines)
    print(report_text)

    # Save to file
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text + "\n")

    # Run pandas check
    results_bundle = {
        "total_revenue": tot_rev,
        "prod_revenue": prod_rev,
        "top_3": top_3_products,
        "mean": mean_val,
        "median": med_val,
    }
    verify_with_pandas(DATA_PATH, results_bundle)
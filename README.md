# Day 2: Sales Analytics Without Pandas

**Tech Hub Kenya — Retail Sales Ingestion & Analytics Pipeline (September 2026)**

---

## 1. Project Overview
Tech Hub Kenya operates retail outlets across five locations: Nairobi CBD, Westgate, Mombasa City Mall, Kisumu Mega Plaza, and Nakuru Westside. 

This project implements an end-to-end retail revenue analytics pipeline under production-constrained environment rules:
1. **Zero External Dependencies in Production:** Tasks 1 through 7 run entirely on the Python Standard Library (`csv`, `pathlib`, `math`), operating without data frame packages like `pandas`.
2. **Messy Data Sanitization:** Safely parses hand-typed point-of-sale (POS) records, strips localized currency notations, isolates unrecoverable records, and compiles an explicit exclusion audit trail.
3. **Automated Verification:** A Pandas audit step (Task 8) independently ingests and recomputes the headline metrics to verify pure Python calculations.

---

## 2. Repository Structure

```text
day2-sales-analytics/
├── sales_analysis.py          # Complete implementation (Tasks 1-8)
├── data/
│   └── electronics_sales.csv  # Input dataset (50 raw transactions)
├── output/
│   └── sales_report.txt       # Generated sales and audit report
├── requirements.txt           # Environment requirements (pandas for verification)
└── README.md                  # Project documentation and cleaning justification
```

---

## 3. Data Cleaning Rules & Handling Untrusted Values

Out of **50 total raw records** ingested from `electronics_sales.csv`:
* **46 valid records** are parsed, converted, and aggregated.
* **4 invalid records** are skipped with explicit reasons logged.

### Sanitization & Repair Logic (`parse_number`)
Point-of-sale entries frequently include regional currency prefixes and thousands commas:
* **Comma Formatting:** Numbers containing comma separators (e.g., `"38,999"` in row `S-3017`) are stripped of `,` and parsed as valid floats (`38999.0`).
* **Currency Prefixes:** Values containing currency indicators (`KES`, `Ksh`, `$` case-insensitively, e.g., `"KES 18999"` in row `S-3029`) have their prefixes trimmed before numeric casting.
* **Whitespace:** All leading and trailing whitespace is stripped before type conversion.

### Exclusion Rules & Justifications (`convert_rows`)
Rows that cannot be converted without making arbitrary domain assumptions are skipped:

| Sale ID | Field Encountered | Raw Value | Exclusion Reason & Justification |
| :--- | :--- | :--- | :--- |
| **S-3006** | `quantity` | `'two'` | **Non-numeric string:** The quantity was typed as an English word rather than a numeric character. Parsing arbitrary word strings risks introducing silent assumptions into automated till batches. |
| **S-3030** | `unit_price_kes` | `'N/A'` | **Explicit missing indicator:** The unit price was recorded as unlisted/not available. We cannot calculate transaction revenue without imputing an arbitrary price. |
| **S-3035** | `quantity` | `''` (blank) | **Missing value:** Empty quantity field. Omitting transaction volume cannot be resolved without manual cashier verification. |
| **S-3039** | `unit_price_kes` | `''` (blank) | **Missing value:** Empty price field prevents calculating transaction revenue ($quantity \times unit\_price$). |

**Integrity Checks Applied:**
* `quantity > 0 and quantity.is_integer()`: Quantities must be positive whole numbers (fractional units are rejected).
* `unit_price_kes >= 0`: Unit prices must be non-negative (negative values indicating unhandled returns are rejected).

---

## 4. Algorithmic Decisions & Assumptions

* **Revenue Formulation:** Per-transaction revenue is computed as:
  $$\text{revenue} = \text{quantity} \times \text{unit\_price\_kes}$$
* **Dictionary Accumulation (`revenue_by`):** Built strictly with vanilla Python dictionaries using standard key retrieval (`totals.get(key, 0.0) + revenue`), without importing `collections.defaultdict` or `collections.Counter`.
* **Tie-Breaking Rule (`top_n`):** When two products have identical aggregated revenue, ties are broken deterministically by sorting in descending order of revenue followed by ascending alphabetical order of product name:
  ```python
  sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:n]
  ```
* **Single-Pass Min/Max (`minimum_maximum`):** Evaluates minimum and maximum values simultaneously in a single iteration ($O(n)$ time complexity, $O(1)$ auxiliary space) without invoking Python's built-in `min()` or `max()`.
* **Empty Sequence Validation:** `mean()`, `median()`, and `minimum_maximum()` raise a clear `ValueError` when passed an empty list.

---

## 5. How to Run

### Option A: Standard Library Only (No Virtual Environment Needed)
To run Tasks 1 through 7 on any server with a base Python installation:

```bash
python sales_analysis.py
```

### Option B: With Pandas Verification Suite
To run the full suite including Task 8's Pandas comparison:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
# .venv\Scripts\activate       # On Windows PowerShell

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run analysis
python sales_analysis.py
```

---

## 6. Verification Results

Running `verify_with_pandas` on the September 2026 dataset confirms full alignment across all baseline metrics:

* **Total Revenue:** `MATCH` (Pure Python: `KES 1,310,812.00` | Pandas: `KES 1,310,812.00`)
* **Revenue by Product:** `MATCH`
* **Top 3 Products:** `MATCH`
  1. HP 15 Laptop (`KES 389,994.00`)
  2. Hisense 43in Smart TV (`KES 272,993.00`)
  3. Lenovo Tab M10 (`KES 199,992.00`)
* **Mean / Median Transaction Revenue:** `MATCH` (Mean: `KES 28,495.91`, Median: `KES 11,097.00`)

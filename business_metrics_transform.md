# Business Metrics — Transformation Design Document

This document describes how raw `.xlsx` input files are transformed into the Business Metrics WBR report by `transform_business_metrics.py`.

---

## Overview

The Business Metrics report covers **exchange adoption, value competitiveness, and demand coverage** across 13 device categories. Data comes from **7 different source types**, each with its own file format. The transform reads all sources, normalizes device names, computes deltas and year-over-year comparisons, and produces a single structured CSV.

---

## Input Files

All input files live in `input/business_metrics/`. There are **22 files** total: 7 types × 3 timeframes + 1 carry-forward file.

### File Naming Convention

```
<type>_<timeframe>.xlsx
```

| Type | What it measures | Timeframes |
|------|-----------------|------------|
| `dc` | Demand Coverage | weekly, monthly, pytd |
| `comp100` | Competitiveness vs 100% SIC discount | weekly, monthly, pytd |
| `comp75` | Competitiveness vs 75% SIC discount | weekly, monthly, pytd |
| `depth` | Base discount depth as % of SIC | weekly, monthly, pytd |
| `attach` | Attach rate (exchange adoption) | weekly, monthly, pytd |
| `reseller` | Reseller share / attach rate | weekly, monthly, pytd |
| `sweetner` | Sweetner coverage + VM session coverage | weekly, monthly, pytd |

Plus: **`previous_report.csv`** — the output from the last run, used to carry forward OP2 target values and hardcoded rows.

### File Formats

The 7 file types use **5 distinct layouts**:

#### Format A — dc, attach, reseller

```
Group    | subcat       | 2026-9 | 2026-8 | ... | YTD
─────────┼──────────────┼────────┼────────┼─────┼──────
HCTP     | Mobile       | 0.957  | 0.956  | ... | 0.953
         | TV           | 0.734  | 0.723  | ... | 0.718
HCTP     | ...          | ...    | ...    | ... | ...
OHL      | fan          | ...    | ...    | ... | ...
```

- Row 3 is the header (found by searching for "Group" or "subcat")
- Periods are `YYYY-week` for weekly, `M-YYYY` for monthly
- "YTD" column provides the year-to-date aggregate
- Device names vary per file (e.g., "Mobile" in dc, mapped to "WLD" in output)

#### Format B — comp100, comp75

```
         | 2026-10      |        |        | 2026-9       |        |
Category | Ovrl         | Base   | Swtnr  | Ovrl         | Base   | Swtnr
─────────┼──────────────┼────────┼────────┼──────────────┼────────┼──────
Mobile   | 0.638        | 0.591  | 0.980  | 0.655        | 0.574  | 0.957
Ref      | 0.977        | 0.184  | 1.000  | 0.980        | 0.199  | 1.000
```

- Row 0: period labels (spanning 3 columns for comp100: Ovrl/Base/Swtnr; 2 for comp75: Ovrl/Base)
- Row 1: sub-column labels
- Row 2+: data rows, one per device
- Each period×sub_col combination produces a separate metric

#### Format D — depth

```
Category | 2026-10 | 2026-9 | 2026-8 | ...
─────────┼─────────┼────────┼────────┼────
Mobile   | 0.950   | 0.952  | 0.950  | ...
Total    | 0.950   | 0.952  | 0.950  | ...
```

- Simple: one column per period, one value per device
- Only has Mobile/WLD data

#### Format E — sweetner

```
Row 0: "Sponsor and Vm_session by Subcat..."
...
Row 4: (blank)   | 2026-9  |           | 2026-8  |           | ...
Row 5: Rows      | sponsor | vm_session| sponsor | vm_session| ...
Row 6: Total     | 0.308   | 0.045     | 0.206   | 0.056     | ...
Row 7: AC        | 0.001   | 0.346     | ...     | ...       | ...
Row 8: Mobile    | 0.335   | 0.006     | ...     | ...       | ...
```

- Period labels on row 4, sub-column names (sponsor/vm_session) on row 5
- Each period spans 2 columns
- "Sweetner coverage" uses the `sponsor` column, "VM coverage" uses `vm_session`

### Previous Report (OP2 Carry-Forward)

`previous_report.csv` is the output CSV from the **previous run**. It provides:

- **OP2 values**: Monthly operational plan targets (e.g., "94.70%") → displayed in the "OP2" column
- **YTD OP2 values**: Year-to-date OP2 targets → displayed in the "YTD OP2" column
- **Hardcoded rows**: "Used item selection (gap vs SIC)" has no input file — its values are carried forward verbatim from the previous report

The parser handles thousand-separator commas in the previous report (e.g., "1,083" bps) by merging split CSV fields.

---

## Device Name Mapping

Device names differ across input files. The config `device_aliases` section maps each file type's names to the standardized output names:

| Output Name | dc/attach/reseller | comp100 | sweetner |
|-------------|-------------------|---------|----------|
| WLD | Mobile | Mobile | Mobile |
| Laptop | Laptop | Laptop | Laptop |
| Ref | Refrigerator | Refrigerator | Refrigerators |
| WM | WashingMachine | Washing Machine | Laundry |
| AC | AC | Air Conditioners | Air Conditioners |
| TV | TV | TV | TV |
| Fan | fan | Fan | Fan |
| Gas Stove | gasstove | Gas stove | Gas_stoves |

(See `configs/business_metrics.yaml` for the complete mapping.)

---

## Output Structure

### Column Layout

```
# | Category | Metrics | WoW | WK-10 WK-09 ... | | MoM | Mar'26 Feb'26 ... | | OP2 v/s OP2 | | PYTD MTD_YoY | YTD YTD_LY YoY | YTD_OP2 v/s_OP2
                         │     └── weekly ──────┘   │      └── monthly ──────┘   │              │                 │               │
                       bps                        empty                        empty           empty            computed        from prev report
                       delta                       col                          col             col
```

| Column Group | Source | Calculation |
|-------------|--------|-------------|
| **WoW** | — | (latest week − previous week) × 10,000 bps |
| **Weekly** | `*_weekly.xlsx` | Values formatted as percentages |
| **MoM** | — | (latest month − previous month) × 10,000 bps |
| **Monthly** | `*_monthly.xlsx` | Values formatted as percentages |
| **OP2** | `previous_report.csv` | Carried forward from previous run |
| **v/s OP2** | — | (latest month − OP2) × 10,000 bps |
| **PYTD month** | `*_pytd.xlsx` | Same-month value from previous year |
| **MTD YoY** | — | (latest month − PYTD month) × 10,000 bps |
| **YTD** | `*_monthly.xlsx` | "YTD" column from the monthly file |
| **YTD LY** | `*_pytd.xlsx` | "YTD" column from the PYTD file |
| **YoY** | — | (YTD − YTD LY) × 10,000 bps |
| **YTD OP2** | `previous_report.csv` | Carried forward from previous run |
| **v/s YTD OP2** | — | (YTD − YTD OP2) × 10,000 bps |

### Row Layout

The report is organized as **Groups → Sections → Data Rows**:

```
5. Business Metrics                         ← title

HCTP                                        ← group header
   Coverage of Exchange                     ← section header
     1  WLD    Demand Coverage              ← data row
     2  WLD    Used item selection          ← hardcoded from previous report
     3  Laptop Demand Coverage
     4  Ref    Demand Coverage
     5  WM     Demand Coverage
     6  AC     Demand Coverage
     7  TV     Demand Coverage

   Exchange Value Competitiveness
     8  WLD    Base discount comp. vs 75% SIC ...
     9  WLD    Base discount comp. vs 100% SIC ...
    10  WLD    Base discount depth ...
    11  WLD    Sweetner Comp
    12  WLD    Overall Comp (Vs 75% SIC)
    13  Laptop Overall Comp (Vs 100% SIC)
    14  Laptop Base 75%
    15  Laptop Base 100%
    16  Laptop Sweetner Comp
    17  Ref    Overall Comp
    18  WM     Overall Comp
    19  AC     Overall Comp
    20  TV     Overall Comp

   Exchange Adoption
    21  WLD    Attach (incl. reseller)
    22  WLD    Reseller share
    23  WLD    Sweetner coverage
    24  Laptop Attach
    ...
    39  TV     VM coverage

OHL                                         ← group header
   Exchange Value Competitiveness
    40  Fan             Overall Comp
    41  Mixer_Grinder   Overall Comp
    42  Vacuum_Cleaner  Overall Comp
    43  Water_heater    Overall Comp
    44  Waterpurifier   Overall Comp
    45  Gas Stove       Overall Comp
    46  Pressure Cooker Overall Comp
```

Total: **46 data rows** across 2 groups and 4 sections.

---

## Transformation Steps

### Step 1: Load all input files

Each of the 7 file types × 3 timeframes is loaded using its format-specific parser. Device names are normalized to the output display name via `device_aliases`. All data is stored in a unified `DataStore` that provides `get_value(device, file_type, sub_col, timeframe, period_label)`.

### Step 2: Load previous report

The `previous_report.csv` is parsed to extract:
- OP2 values keyed by (device, metric)
- YTD OP2 values keyed by (device, metric)
- Complete rows for hardcoded metrics (Used item selection)

Thousand-separator commas in bps values are repaired during parsing.

### Step 3: Determine period labels

- **Weekly**: Parsed from `YYYY-week` format → sorted descending (e.g., WK-10, WK-09, ...)
- **Monthly**: Parsed from `M-YYYY` or `YYYY-M` → sorted descending (e.g., Mar'26, Feb'26, ...)
- **PYTD**: Same format as monthly but from previous year files. The month matching today's month is selected for MTD YoY comparison.

### Step 4: Build data rows

For each row defined in the config (`groups → sections → rows`):

1. **Get raw values** from the DataStore for all weekly and monthly periods
2. **Compute WoW**: `(latest_week − previous_week) × 10,000` bps
3. **Compute MoM**: `(latest_month − previous_month) × 10,000` bps
4. **Look up OP2** from previous report, compute v/s OP2
5. **Look up PYTD month** value, compute MTD YoY
6. **Get YTD and YTD LY** from the "Total"/"YTD" columns in monthly and PYTD files
7. **Compute YoY**: `(YTD − YTD LY) × 10,000` bps
8. **Look up YTD OP2** from previous report, compute v/s YTD OP2
9. **Format all percentage values** as "XX.XX%" strings

For hardcoded rows (Used item selection), the entire row is carried verbatim from the previous report.

### Step 5: Write CSV

All rows are assembled with the header and written to `output/business_metrics/report.csv`.

---

## Configuration Reference

The config file `configs/business_metrics.yaml` controls:

### `title`
Report title displayed in row 1 of the output.

### `device_aliases`
Maps input file device names to output display names, per file type. Uses YAML anchors (`&dc_aliases` / `*dc_aliases`) to share common mappings.

### `groups`
Defines the row layout:

```yaml
groups:
  HCTP:                                    # group name (displayed as header)
    sections:
      - name: "Coverage of Exchange"       # section name (displayed as sub-header)
        rows:
          - device: WLD                    # output device name
            metric: "Demand Coverage"      # metric label
            file_type: dc                  # which input file type to read
          - device: WLD
            metric: "Used item selection"
            file_type: hardcoded           # carried from previous_report.csv
          - device: WLD
            metric: "Sweetner Comp"
            file_type: comp100
            sub_col: Swtnr                 # which sub-column (for multi-column files)
```

Each row specifies:
- `device`: The normalized device name (must match a value in `device_aliases`)
- `metric`: The display label for this row
- `file_type`: Which input file to read (`dc`, `comp100`, `comp75`, `depth`, `attach`, `reseller`, `sweetner`, or `hardcoded`)
- `sub_col` (optional): For multi-column files (comp100, comp75, sweetner), which sub-column to use (`Ovrl`, `Base`, `Swtnr`, `sponsor`, `vm_session`)

---

## How to Update for a New Period

1. Replace the 21 xlsx files in `input/business_metrics/` with the latest data
2. Copy the current `output/business_metrics/report.csv` to `input/business_metrics/previous_report.csv`
3. Run:
   ```bash
   python3 run.py business_metrics
   ```
4. The new report appears at `output/business_metrics/report.csv`

The OP2 values from the previous report are carried forward automatically. The PYTD month is auto-detected based on today's date.

---

## How to Add a New Device or Metric Row

1. Add the device alias to the relevant file type(s) in `device_aliases`
2. Add a new row entry under the appropriate group → section in `groups`
3. Ensure the input file contains data for that device
4. Re-run — the new row appears in the output

No code changes required.

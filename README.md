# Exchange WBR — CPU Report Generator

Transforms raw per-reason CPU metrics (`.xlsx` files) into a structured Weekly Business Review (WBR) report (`.csv`).

---

## High-Level Picture

```
 ┌──────────────────────────────────────────────────────────────┐
 │                    INPUT (per device)                        │
 │  Up to 4 xlsx files: weekly, monthly, quarterly, pytd       │
 │  Each file: wide format — periods as column groups,         │
 │             one row per contact reason + one "Total" row     │
 └──────────────────────┬───────────────────────────────────────┘
                        │
          ┌─────────────▼──────────────┐
          │      transform.py          │
          │  (config.yaml drives it)   │
          └─────────────┬──────────────┘
                        │
 ┌──────────────────────▼───────────────────────────────────────┐
 │                      OUTPUT                                  │
 │  Single CSV: all devices stacked, hierarchical row layout,   │
 │  all timelines side-by-side in columns                       │
 └──────────────────────────────────────────────────────────────┘
```

---

## Input File Format (`.xlsx`)

Every input file has the same wide layout:

| | Period-A | | | ... | Period-B | | | ... | Total | | | ... |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **(row 0)** | `2026-9` | | | | `2026-8` | | | | `Total` | | | |
| **(row 1)** | CPU | Pre-PDD | PDD | Post-PDD Gen ... | CPU | Pre-PDD | ... | | CPU | Pre-PDD | ... | |
| Total | 0.200 | 0.021 | 0.098 | ... | 0.217 | 0.022 | ... | | | | | |
| check order status | 0.059 | 0.007 | 0.034 | ... | 0.059 | 0.007 | ... | | | | | |
| ... | | | | | | | | | | | | |

- **Row 0**: Period headers across columns (e.g., `2026-9`, `2026-8`, ... plus a `Total` block).
- **Row 1**: The 12 metric names repeated under each period — `CPU`, `Pre-PDD`, `PDD`, `Post-PDD`, `Gen`, `Pre-PDD Gen`, `PDD_Gen`, `Post-PDD Gen`, `Spl`, `Pre-PDD Spl`, `PDD Spl`, `Post-PDD Spl`.
- **Row 2 ("Total")**: The true aggregate values for each metric per period. This row is **not** the sum of the reason rows — it comes from a separate source and is the authoritative aggregate.
- **Rows 3+**: One row per contact reason, with values for every (period × metric) cell.

The four file types differ only in what the period headers represent:

| File | Period format | Example periods |
|---|---|---|
| Weekly | `YYYY-W` (year-week) | `2026-9`, `2026-8`, ..., `2026-1` |
| Monthly | `YYYY-M` (year-month) | `2026-2`, `2026-1`, `2025-12`, ... |
| Quarterly | `YYYY-Q` (year-quarter) | `2026-1`, `2025-4`, `2025-3`, ... |
| PYTD | `YYYY-Q` (previous year quarters) | `2025-1`, `2025-2` |

---

## Transformation Pipeline — Step by Step

### Step 1: Auto-discover input files

The script scans the `input/` folder for files matching the naming convention (case-insensitive):

```
CPU_<device-tag>_<timeframe>.xlsx
```

| Device tag | Config key | | Timeframe |
|---|---|---|---|
| `mob` | mobile | | `weekly` |
| `tv` | tv | | `monthly` |
| `ac` | ac | | `quarterly` |
| `ref` | refrigerator | | `pytd` |
| `wm` | wm | | |

Examples: `CPU_mob_weekly.xlsx`, `CPU_TV_Monthly.xlsx`, `CPU_ref_pytd.xlsx`

The script validates that every timeframe declared in `config.yaml` under a device's `timeframes` list has a corresponding file. If any are missing, it exits with an error listing exactly which files are expected.

### Step 2: Load and unpivot each xlsx file

Each `.xlsx` is in **wide format** (periods as column groups). The loader:

1. Reads the first row to extract period headers and their column positions.
2. Skips the second row (metric names — they follow a fixed order).
3. Discards the `Total` **period block** (the aggregated-across-all-periods column group).
4. For each data row (reason), iterates over every period block and extracts the 12 metric values.
5. Produces a **long-format DataFrame**: one row per `(reason, period)` with columns `reason`, `Time_Frame`, `CPU`, `Pre-PDD`, `PDD`, `Post-PDD`, `Gen`, `Pre-PDD Gen`, `PDD_Gen`, `Post-PDD Gen`, `Spl`, `Pre-PDD Spl`, `PDD Spl`, `Post-PDD Spl`.

### Step 3: Parse time-frame labels

Each raw period string (e.g., `2026-9`) is parsed into a sort key and a display label:

| File type | Raw value | Sort key | Display label |
|---|---|---|---|
| Weekly | `2026-9` | `(2026, 9)` | `Wk-09` |
| Monthly | `2026-2` | `(2026, 2)` | `Feb'26` |
| Quarterly | `2025-4` | `(2025, 4)` | `Q4'25` |
| PYTD | `2025-1` | `(2025, 1)` | `Q1'25` |

Labels are sorted descending (most recent first) to form the column order.

### Step 4: Filter out future periods

For monthly and quarterly files, any period that falls **after today's date** is dropped. This handles known data glitches where the source files contain placeholder rows for future months/quarters (e.g., `Dec'26` when it's currently Feb 2026). Weekly data is not filtered (assumed to only contain past weeks).

### Step 5: Build the output column layout

All timelines are arranged side-by-side with empty separator columns between groups:

```
 #  Metrics  WoW  Wk-09 Wk-08 ...    MoM  Feb'26 Jan'26 ...    QoQ  Q1'26 Q4'25 ...    YTD'26  PYTD'25
              │                       │                         │                          │        │
         basis-point               empty                     empty                       empty    PYTD
         delta between             col                       col                         col      average
         2 most recent                                                                   │
         weeks                                                                     average of
                                                                                   current-year
                                                                                   quarters
```

### Step 6: Determine segments per device

Each device in `config.yaml` declares which segments to include:

- **Mobile**: `[overall, generalist, specialist]` — all three row groups.
- **TV, AC, Refrigerator, WM**: `[overall]` — only the overall row group.

Each segment maps to a specific set of source columns:

| Segment | CPU column | Pre-PDD column | PDD column | Post-PDD column |
|---|---|---|---|---|
| Overall | `CPU` | `Pre-PDD` | `PDD` | `Post-PDD` |
| Generalist | `Gen` | `Pre-PDD Gen` | `PDD_Gen` | `Post-PDD Gen` |
| Specialist | `Spl` | `Pre-PDD Spl` | `PDD Spl` | `Post-PDD Spl` |

### Step 7: Resolve top 3 reasons per (segment × phase)

For each combination of segment and delivery phase (Pre-PDD / PDD / Post-PDD), the script determines which 3 reasons to display:

- **Config-specified**: If `config.yaml` lists explicit reason strings for that `(segment, phase)`, those exact reasons are used.
- **Auto-detected**: If set to `auto` or omitted, the script ranks all reasons (excluding blank and "Total") by the sum of their values across all weeks for the relevant metric column, and picks the top 3.

The same 3 reasons are used consistently across all timelines (weekly, monthly, quarterly, PYTD).

### Step 8: Extract values and build hierarchical rows

For each device, the script generates a nested row structure. Within each segment:

```
[Segment header]                        ← only for Generalist/Specialist
  Contacts per unit (CPU)               ← aggregate row from "Total" reason
  Pre-PDD CPU                           ← aggregate row from "Total" reason
    Reason 1 - <reason name>            ← individual reason values
    Reason 2 - <reason name>
    Reason 3 - <reason name>
  PDD - CPU                             ← aggregate row
    Reason 1 ...
    Reason 2 ...
    Reason 3 ...
  Post-PDD CPU                          ← aggregate row
    Reason 1 ...
    Reason 2 ...
    Reason 3 ...
```

**Aggregate rows** (like "Contacts per unit (CPU)" and phase headers) pull values from the `Total` reason row in the data — the true aggregate, not a sum of individual reasons. If no `Total` row exists, it falls back to summing all reason values.

**Reason rows** pull values for that specific reason from each time period.

### Step 9: Compute period-over-period deltas

For each row, the script computes a change column expressed in **basis points** (value × 10,000):

| Column | Calculation |
|---|---|
| **WoW** | `(Wk-09 value − Wk-08 value) × 10,000` |
| **MoM** | `(most recent month − previous month) × 10,000` |
| **QoQ** | `(most recent quarter − previous quarter) × 10,000` |

A value of `-136` means the metric decreased by 136 basis points (0.0136) week-over-week.

### Step 10: Compute YTD and PYTD averages

- **YTD'26** (current year-to-date): Average of all current-year quarters from the quarterly file. If only Q1'26 data exists, YTD = Q1'26. As Q2, Q3, Q4 arrive, they are included in the average.
- **PYTD'25** (previous year-to-date): Average of all quarters from the PYTD file. Individual PYTD quarter columns are **not** shown — only the single average.

### Step 11: Stack devices and write CSV

All device sections are stacked vertically in the output, separated by blank rows. Each device gets:
- A title row (e.g., "CPU (Mobiles)")
- Its own row numbering starting at 1
- Only its configured segments

The final CSV is written with a global title row ("Exchange WBR - CPU"), a blank row, the shared header row, then all device sections.

---

## Output Structure

```
Row 1:  Exchange WBR - CPU                          (title)
Row 2:  (blank)
Row 3:  # | Metrics | WoW | Wk-09 | ... |  | MoM | Feb'26 | ... |  | QoQ | Q1'26 | ... |  | YTD'26 | PYTD'25
Row 4:  (blank separator)
Row 5:  CPU (Mobiles)                               (device title)
Row 6:  1 | Contacts per unit (CPU) | -164 | 0.2001 | 0.2165 | ...
Row 7:  2 | Pre-PDD CPU | -4 | 0.0213 | ...
Row 8:  3 | Reason 1 - check order status tracking | ...
Row 9:  4 | Reason 2 - request for early delivery | ...
Row 10: 5 | Reason 3 - reschedule delivery | ...
Row 11: 6 | PDD - CPU | 107 | ...
...
Row 19: 14 | Generalist                             (segment header)
Row 20: 15 | Contacts per unit (CPU) | ...
...
Row 33: 28 | Specialist                             (segment header)
...
Row 47: (blank separator)
Row 48: CPU (TV)                                    (next device)
Row 49: 1 | Contacts per unit (CPU) | ...           (numbering restarts)
...
```

---

## Project Structure

```
exchange_wbr/
├── transform.py          ← main script (all transformation logic)
├── config.yaml           ← per-device settings: segments, reasons, timeframes
├── requirements.txt      ← pandas, pyyaml, openpyxl
├── input/                ← drop xlsx files here (auto-discovered)
│   ├── CPU_mob_weekly.xlsx
│   ├── CPU_mob_monthly.xlsx
│   ├── CPU_TV_Weekly.xlsx
│   └── ...
├── report.csv            ← generated output
└── .vscode/
    └── launch.json       ← hit F5 to run
```

---

## Configuration (`config.yaml`)

Each device block controls:

```yaml
devices:
  mobile:
    title: "CPU (Mobiles)"                          # display name in output
    segments: [overall, generalist, specialist]      # which row groups to include
    timeframes: [weekly, monthly, quarterly, pytd]   # which files are required
    reasons:                                         # top 3 reasons per segment × phase
      overall:
        pre_pdd:
          - "check order status tracking"
          - "request for early delivery"
          - "reschedule delivery"
        pdd: auto                                    # auto-detect from data
        post_pdd:
          - "check order status tracking"
          - "check refund status"
          - "late shipment"
      generalist:
        pre_pdd:                                     # can differ from overall
          - "check order status tracking"
          - "request for early delivery"
          - "check refund status"
        # ...
  tv:
    title: "CPU (TV)"
    segments: [overall]                              # no generalist/specialist
    timeframes: [weekly, monthly, quarterly, pytd]
    reasons:
      overall:
        pre_pdd: [...]
        pdd: [...]
        post_pdd: [...]
```

---

## Usage

**Default (process all devices in config):**
```bash
python3 transform.py
```

**Specific devices:**
```bash
python3 transform.py mobile tv
```

**Limit weekly columns:**
```bash
python3 transform.py --num-weeks 6
```

**Override a file via CLI (single-device only):**
```bash
python3 transform.py mobile --weekly /path/to/file.xlsx -o report.csv
```

**Or just hit F5 in Cursor/VS Code** — `launch.json` is pre-configured.

---

## Key Design Decisions

1. **"Total" row = true aggregate**: The `Total` row in each xlsx provides authoritative aggregate values. Individual reason rows do not sum to the Total — they are a breakdown, not a partition. The script uses Total for aggregate lines and excludes it from reason ranking.

2. **Reasons are uniform across timelines**: The same 3 reasons chosen for a (segment × phase) apply to weekly, monthly, quarterly, and PYTD columns. This keeps the report rows consistent.

3. **Future-period filtering**: Monthly and quarterly data beyond today's date is silently dropped, guarding against placeholder/glitch data in source files.

4. **File discovery is case-insensitive**: `CPU_MOB_WEEKLY.xlsx` and `cpu_mob_weekly.xlsx` are treated identically.

5. **Graceful degradation**: If a non-required xlsx file is missing (not in `timeframes`), that timeline section is simply omitted from the output. Only files listed in `timeframes` trigger a hard error when absent.

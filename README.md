# Exchange WBR — Report Generator

Transforms raw operational data (`.xlsx` files) into structured Weekly Business Review (WBR) reports. Supports multiple metrics, each with its own transformation logic, input format, and output structure.

---

## Project Structure

```
exchange_wbr/
├── run.py                          # main entry point — installs deps, dispatches to metrics
├── config.yaml                     # global config — lists which metrics to run
├── transform_cpu.py                # CPU metric transformation logic
├── transform_business_metrics.py   # Business Metrics transformation logic
├── configs/
│   ├── cpu.yaml                    # CPU-specific config (devices, segments, reasons)
│   └── business_metrics.yaml       # Business Metrics config (groups, sections, device aliases)
├── input/
│   ├── cpu/                        # CPU xlsx files (auto-discovered by naming convention)
│   │   ├── CPU_mob_weekly.xlsx
│   │   ├── CPU_TV_Monthly.xlsx
│   │   └── ...
│   └── business_metrics/           # Business Metrics xlsx files (7 types × 3 timeframes)
│       ├── dc_weekly.xlsx
│       ├── comp100_monthly.xlsx
│       ├── sweetner_pytd.xlsx
│       ├── previous_report.csv     # OP2 carry-forward from last run
│       └── ...
├── output/
│   ├── cpu/
│   │   └── report.csv
│   └── business_metrics/
│       └── report.csv
├── requirements.txt
├── .gitignore
├── cursor_row_and_column_heading_transform.md   # CPU metric design doc
├── business_metrics_transform.md                # Business Metrics design doc
└── .vscode/
    └── launch.json                 # F5 to run (3 configurations)
```

---

## Quick Start

### Option 1: Run everything

Hit **F5** in Cursor/VS Code (select "Generate All Reports"), or:

```bash
python3 run.py
```

This processes every metric listed in `config.yaml` and generates reports under `output/`.

### Option 2: Run a specific metric

```bash
python3 run.py cpu
python3 run.py business_metrics
python3 run.py cpu business_metrics    # run both
```

Or use the dedicated launch configurations in VS Code (F5 → pick from dropdown).

### Option 3: Run a metric standalone

```bash
python3 transform_cpu.py
python3 transform_business_metrics.py
```

---

## Dependencies

Dependencies are auto-installed on first run via `run.py`. Manual install:

```bash
pip install pandas pyyaml openpyxl
```

---

## Metrics

### 1. CPU Metric

Transforms per-reason contact data into a hierarchical report.

| Aspect | Details |
|--------|---------|
| **Input files** | 4 xlsx per device: `CPU_<device>_<timeframe>.xlsx` |
| **Devices** | Mobile, TV, AC, Refrigerator, Washing Machine |
| **Row hierarchy** | Segment (Overall / Generalist / Specialist) → Phase (Pre-PDD / PDD / Post-PDD) → Top 3 reasons |
| **Column layout** | WoW + weekly \| MoM + monthly \| QoQ + quarterly \| YTD \| PYTD |
| **Config** | `configs/cpu.yaml` — devices, segments, reasons, timeframes |
| **Input folder** | `input/cpu/` — naming: `CPU_<device>_<timeframe>.xlsx` (case-insensitive) |
| **Output** | `output/cpu/report.csv` |
| **Design doc** | `cursor_row_and_column_heading_transform.md` |

### 2. Business Metrics

Transforms exchange adoption, competitiveness, and coverage data from 7 source types into a single report with 46 data rows across HCTP and OHL device groups.

| Aspect | Details |
|--------|---------|
| **Input files** | 21 xlsx files (7 types × 3 timeframes) + `previous_report.csv` |
| **File types** | dc, comp100, comp75, depth, attach, reseller, sweetner |
| **Timeframes** | weekly, monthly, pytd |
| **Devices** | WLD, Laptop, Ref, WM, AC, TV, Fan, Mixer_Grinder, Vacuum_Cleaner, Water_heater, Waterpurifier, Gas Stove, Pressure Cooker |
| **Groups** | HCTP (Coverage, Competitiveness, Adoption) + OHL (Competitiveness) |
| **Column layout** | WoW + weekly \| MoM + monthly \| OP2 + v/s OP2 \| PYTD + MTD YoY \| YTD + YTD LY + YoY \| YTD OP2 + v/s OP2 |
| **Config** | `configs/business_metrics.yaml` — device aliases, row layout, file types |
| **Input folder** | `input/business_metrics/` — naming: `<type>_<timeframe>.xlsx` |
| **Output** | `output/business_metrics/report.csv` |
| **Design doc** | `business_metrics_transform.md` |

---

## Adding a New Metric

1. Create `transform_<metric>.py` with a `run(config_path, input_dir, output_dir)` function
2. Create `configs/<metric>.yaml` with whatever config your metric needs
3. Create `input/<metric>/` folder for input files
4. Add the metric name to `config.yaml`:

   ```yaml
   metrics:
     - cpu
     - business_metrics
     - <metric>
   ```

5. Hit F5 — the dispatcher will pick it up automatically

Each metric is fully independent — its own columns, hierarchy, file format, and transformation logic.

# Automated Data Processing & Reporting System

An end-to-end **ETL + reporting pipeline** that ingests raw sales data (CSV), cleans and transforms it with **Pandas**, loads it into **MySQL**, and generates polished **Excel reports with charts** — all runnable on-demand or on an automated schedule.

Built with: **Python · Pandas · SQL · MySQL · SQLAlchemy · OpenPyXL · Matplotlib**

---

## Features

- **Extract** — reads raw CSV sales data (easily extendable to APIs / other file sources).
- **Transform** — Pandas-based cleaning: strips/normalizes text, parses dates, drops duplicates and invalid rows (negative quantity, missing customer, unparsable dates), computes derived fields (`total_amount`, `order_year`, `order_month`).
- **Load** — bulk-loads cleaned data into MySQL via SQLAlchemy, with a `UNIQUE` key on `order_id` to prevent duplicate loads, plus an upserted monthly summary table for fast reporting.
- **Report** — generates a multi-sheet Excel workbook (revenue by region, by category, top products, monthly trend) with embedded native Excel charts, plus standalone PNG charts via Matplotlib.
- **Audit log** — every ETL run is logged to an `etl_run_log` table (rows read/cleaned/rejected/loaded, status, duration) for traceability.
- **Automation** — a built-in scheduler (`schedule` library) runs the full pipeline daily, or trigger it manually / via cron / via GitHub Actions.
- **Tested** — Pandas cleaning/aggregation logic is fully unit-tested with `pytest` (no live DB required to run tests).

---

## Architecture

```
                 ┌───────────────┐
   raw CSV  ───▶  │   EXTRACT     │
                 └──────┬────────┘
                        ▼
                 ┌───────────────┐
                 │  TRANSFORM    │   (Pandas: clean, validate, aggregate)
                 │  data_processor.py
                 └──────┬────────┘
                        ▼
                 ┌───────────────┐
                 │    LOAD       │   (SQLAlchemy → MySQL)
                 │  db_connector.py
                 └──────┬────────┘
                        ▼
              ┌────────────────────┐
              │      MySQL         │
              │  sales_transactions │
              │  monthly_region_summary
              │  etl_run_log        │
              └─────────┬──────────┘
                        ▼
                 ┌───────────────┐
                 │    REPORT     │   (Excel + charts + PNGs)
                 │ report_generator.py
                 └───────────────┘
```

---

## Project Structure

```
automated-data-processing-reporting-system/
├── data/
│   └── raw_sales_data.csv        # sample dataset (1500+ rows, intentionally messy)
├── sql/
│   └── schema.sql                # MySQL DDL: tables, indexes, sample queries
├── src/
│   ├── config_loader.py          # loads config.yaml + .env overrides
│   ├── data_processor.py         # Pandas cleaning & aggregation logic
│   ├── db_connector.py           # MySQL connection + load/query helpers
│   ├── etl_pipeline.py           # Extract → Transform → Load orchestrator
│   ├── report_generator.py       # Builds Excel report + Matplotlib charts
│   └── logger.py                 # Rotating file + console logger
├── tests/
│   └── test_data_processor.py    # pytest unit tests (10 tests, no DB needed)
├── config/
│   └── config.yaml.example       # copy to config.yaml and edit
├── reports/                      # generated Excel/PNG reports land here
├── logs/                         # pipeline.log (rotating)
├── .github/workflows/ci.yml      # GitHub Actions: runs tests on every push
├── main.py                       # CLI entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/<your-username>/automated-data-processing-reporting-system.git
cd automated-data-processing-reporting-system
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up MySQL

Make sure MySQL Server is running, then create the schema:

```bash
mysql -u root -p < sql/schema.sql
```

This creates the `sales_reporting_db` database with three tables: `sales_transactions`, `monthly_region_summary`, and `etl_run_log`.

### 3. Configure credentials

```bash
cp config/config.yaml.example config/config.yaml
# edit config/config.yaml with your MySQL host/user/password
```

Or use environment variables instead (copy `.env.example` to `.env`) — env vars override `config.yaml`.

---

## Usage

Run the ETL pipeline (extract → clean → load into MySQL):

```bash
python main.py etl --source data/raw_sales_data.csv
```

Generate the Excel + chart report from what's in MySQL:

```bash
python main.py report
```

Run both in one shot:

```bash
python main.py run-all --source data/raw_sales_data.csv
```

Run automatically every day at a fixed time (e.g. 2 AM):

```bash
python main.py schedule --source data/raw_sales_data.csv --time 02:00
```

> For production automation, prefer a system **cron job** or a **GitHub Actions scheduled workflow** calling `python main.py run-all` over keeping a Python process alive — the `schedule` command is provided for convenience/demo purposes.

---

## Sample Output

Each ETL run prints/logs a summary like:

```
{'rows_read': 1515, 'rows_cleaned': 1458, 'rows_rejected': 57, 'rows_loaded': 1458, 'status': 'SUCCESS', 'duration_seconds': 2.1}
```

The generated Excel report (`reports/sales_report_<timestamp>.xlsx`) includes:
- **Summary** — total revenue & orders
- **By Region** — revenue table + bar chart
- **By Category** — revenue table + bar chart
- **Top Products** — top 10 products by revenue
- **Monthly Trend** — revenue over time table + line chart

---

## Testing

```bash
pytest tests/ -v
```

10 unit tests validate schema checks, deduplication, invalid-row filtering, text normalization, `total_amount` math, and all aggregation functions — using in-memory DataFrames, so no MySQL connection is required to run them. CI runs these automatically on every push via GitHub Actions.

---

## Extending This Project

- Swap the CSV `extract()` step for an API pull, S3 bucket, or another database.
- Add an `upsert` mode to `db_connector.load_dataframe` using a MySQL staging table + `INSERT ... ON DUPLICATE KEY UPDATE` for true incremental refresh.
- Add email delivery of the generated Excel report (e.g. via `smtplib` or a transactional email API).
- Containerize with Docker Compose (Python app + MySQL) for one-command setup.
- Add a lightweight dashboard (Streamlit/Flask) on top of the MySQL summary tables.

---

## License

MIT License — free to use, modify, and distribute.

# Sales & Transaction Analytics Dashboard

A simple, job-ready analytics project that:
- Reads **CSV transactions & customers**
- Computes **KPIs** (Revenue, Orders, Customers, AOV, Repeat Rate)
- Builds an **Excel dashboard** (pivot-style summaries + charts)
- Exports a **clean HTML summary** for quick viewing
- Includes **sample data** so it works out-of-the-box

---

## Project Structure

Sales-and-Transaction-Analytics-Dashboard/
├─ src/
│   ├─ query.sql         # sample SQL for common analytics
│   └─ analyze.py        # Python pipeline to build outputs
├─ data/
│   ├─ transactions.csv  # sample transactions data
│   └─ customers.csv     # sample customers data
├─ output/
│   ├─ dashboard.xlsx    # generated: KPIs, tables, charts
│   └─ summary.html      # generated: HTML snapshot
├─ README.md
└─ benchmark.md

---

## Project Instructions

### Set the Environment, Run
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install pandas numpy xlsxwriter python-dateutil

python src/analyze.py
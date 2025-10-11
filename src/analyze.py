"""
Sales & Transaction Analytics Dashboard
Reads CSVs (data/transactions.csv, data/customers.csv),
computes KPIs & summaries, and writes:
  - output/dashboard.xlsx (pivot-style summaries + charts)
  - output/summary.html   (lightweight HTML snapshot)

Run:
  python src/analyze.py

Dependencies:
  pip install pandas numpy xlsxwriter python-dateutil
"""

from __future__ import annotations
import os
from datetime import datetime
import pandas as pd
import numpy as np

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "output")

TXN_CSV = os.path.join(DATA_DIR, "transactions.csv")
CUS_CSV = os.path.join(DATA_DIR, "customers.csv")

EXCEL_OUT = os.path.join(OUT_DIR, "dashboard.xlsx")
HTML_OUT  = os.path.join(OUT_DIR, "summary.html")

# Helpers
def ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

def seed_sample_data() -> None:
    """
    Creates small sample CSVs if not present, so the project
    works out-of-the-box.
    """
    if not os.path.exists(CUS_CSV):
        customers = pd.DataFrame([
            {"customer_id": "C001", "signup_date": "2024-12-15", "segment": "Retail",     "channel": "Online"},
            {"customer_id": "C002", "signup_date": "2025-01-10", "segment": "SMB",        "channel": "Partner"},
            {"customer_id": "C003", "signup_date": "2025-01-20", "segment": "Enterprise", "channel": "Direct"},
            {"customer_id": "C004", "signup_date": "2025-02-05", "segment": "Retail",     "channel": "Online"},
            {"customer_id": "C005", "signup_date": "2025-02-15", "segment": "SMB",        "channel": "Online"},
        ])
        customers.to_csv(CUS_CSV, index=False)

    if not os.path.exists(TXN_CSV):
        txns = pd.DataFrame([
            {"txn_id": "T1001", "txn_date": "2025-01-05", "customer_id": "C001", "product": "Basic",    "quantity": 1, "unit_price": 49.0,  "currency": "USD"},
            {"txn_id": "T1002", "txn_date": "2025-01-15", "customer_id": "C002", "product": "Pro",      "quantity": 1, "unit_price": 149.0, "currency": "USD"},
            {"txn_id": "T1003", "txn_date": "2025-01-22", "customer_id": "C003", "product": "Enterprise","quantity": 1,"unit_price": 499.0, "currency": "USD"},
            {"txn_id": "T1004", "txn_date": "2025-02-01", "customer_id": "C001", "product": "Basic",    "quantity": 2, "unit_price": 49.0,  "currency": "USD"},
            {"txn_id": "T1005", "txn_date": "2025-02-10", "customer_id": "C004", "product": "Basic",    "quantity": 1, "unit_price": 49.0,  "currency": "USD"},
            {"txn_id": "T1006", "txn_date": "2025-02-20", "customer_id": "C005", "product": "Pro",      "quantity": 1, "unit_price": 149.0, "currency": "USD"},
            {"txn_id": "T1007", "txn_date": "2025-03-03", "customer_id": "C003", "product": "Enterprise","quantity": 1,"unit_price": 499.0, "currency": "USD"},
            {"txn_id": "T1008", "txn_date": "2025-03-12", "customer_id": "C002", "product": "Pro",      "quantity": 1, "unit_price": 149.0, "currency": "USD"},
            {"txn_id": "T1009", "txn_date": "2025-03-18", "customer_id": "C001", "product": "Basic",    "quantity": 1, "unit_price": 49.0,  "currency": "USD"},
        ])
        txns.to_csv(TXN_CSV, index=False)

def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    customers = pd.read_csv(CUS_CSV, parse_dates=["signup_date"])
    txns = pd.read_csv(TXN_CSV, parse_dates=["txn_date"])
    # Basic sanity
    txns = txns.dropna(subset=["txn_id", "txn_date", "customer_id", "product", "quantity", "unit_price"])
    txns["amount"] = txns["quantity"] * txns["unit_price"]
    txns["date"] = txns["txn_date"].dt.date
    txns["month"] = txns["txn_date"].values.astype("datetime64[M]")
    customers["cohort_month"] = customers["signup_date"].values.astype("datetime64[M]")
    
    return customers, txns

def compute_kpis(customers: pd.DataFrame, txns: pd.DataFrame) -> dict:
    total_revenue = txns["amount"].sum()
    orders = txns["txn_id"].nunique()
    customers_count = customers["customer_id"].nunique()
    aov = (txns.groupby("txn_id")["amount"].sum().mean()) if orders else 0.0

    # New vs Returning (monthly)
    first_txn = txns.groupby("customer_id")["txn_date"].min().rename("first_txn_date")
    tx_enriched = txns.merge(first_txn, on="customer_id", how="left")
    tx_enriched["customer_type"] = np.where(
        tx_enriched["txn_date"].dt.to_period("M") == tx_enriched["first_txn_date"].dt.to_period("M"),
        "New", "Returning"
    )

    monthly = (txns
               .groupby("month")["amount"]
               .sum()
               .reset_index()
               .rename(columns={"amount": "revenue"}))

    top_products = (txns.groupby("product")
                    .agg(units_sold=("quantity", "sum"),
                         revenue=("amount", "sum"))
                    .reset_index()
                    .sort_values("revenue", ascending=False))

    by_channel = (txns.merge(customers[["customer_id", "segment", "channel"]], on="customer_id", how="left")
                  .groupby(["segment", "channel"])
                  .agg(revenue=("amount", "sum"),
                       orders=("txn_id", "nunique"))
                  .reset_index()
                  .sort_values("revenue", ascending=False))

    repeat_rate = (tx_enriched.query("customer_type == 'Returning'")["txn_id"].nunique() /
                   orders) if orders else 0.0

    kpis = {
        "total_revenue": float(total_revenue),
        "orders": int(orders),
        "customers": int(customers_count),
        "aov": float(aov),
        "repeat_order_rate": float(repeat_rate),
        "monthly": monthly,
        "top_products": top_products,
        "by_channel": by_channel,
        "tx_enriched": tx_enriched
    }
    return kpis

def write_excel(kpis: dict) -> None:
    with pd.ExcelWriter(EXCEL_OUT, engine="xlsxwriter", datetime_format="yyyy-mm-dd") as writer:
        # Sheets with data
        kpis["monthly"].to_excel(writer, sheet_name="MonthlyRevenue", index=False)
        kpis["top_products"].to_excel(writer, sheet_name="TopProducts", index=False)
        kpis["by_channel"].to_excel(writer, sheet_name="SegmentChannel", index=False)
        kpis["tx_enriched"].to_excel(writer, sheet_name="Transactions", index=False)

        wb = writer.book

        # Dashboard sheet
        dash = wb.add_worksheet("Dashboard")
        # Basic formats
        title_fmt = wb.add_format({"bold": True, "font_size": 16})
        kpi_label = wb.add_format({"bold": True, "font_size": 12})
        kpi_value = wb.add_format({"font_size": 12, "num_format": "#,##0.00"})
        currency_fmt = wb.add_format({"num_format": "$#,##0"})
        percent_fmt  = wb.add_format({"num_format": "0.0%"})

        dash.write("A1", "Sales & Transaction Dashboard", title_fmt)
        dash.write("A3", "Generated:", kpi_label)
        dash.write("B3", datetime.now().strftime("%Y-%m-%d %H:%M"))

        # KPI cards
        dash.write("A5", "Total Revenue", kpi_label)
        dash.write("B5", kpis["total_revenue"], currency_fmt)
        dash.write("A6", "Orders", kpi_label)
        dash.write_number("B6", kpis["orders"])
        dash.write("A7", "Customers", kpi_label)
        dash.write_number("B7", kpis["customers"])
        dash.write("A8", "Average Order Value (AOV)", kpi_label)
        dash.write("B8", kpis["aov"], currency_fmt)
        dash.write("A9", "Repeat Order Rate", kpi_label)
        dash.write("B9", kpis["repeat_order_rate"], percent_fmt)

        # Charts use data from other sheets
        # 1) Revenue over time (MonthlyRevenue!A:B)
        chart_rev = wb.add_chart({"type": "line"})
        chart_rev.add_series({
            "name":       "Revenue",
            "categories": "=MonthlyRevenue!$A$2:$A$1048576",
            "values":     "=MonthlyRevenue!$B$2:$B$1048576",
        })
        chart_rev.set_title({"name": "Revenue by Month"})
        chart_rev.set_y_axis({"major_gridlines": {"visible": False}})
        dash.insert_chart("D5", chart_rev, {"x_scale": 1.4, "y_scale": 1.2})

        # 2) Top products by revenue (TopProducts!A:C)
        chart_prod = wb.add_chart({"type": "column"})
        chart_prod.add_series({
            "name":       "Revenue",
            "categories": "=TopProducts!$A$2:$A$11",
            "values":     "=TopProducts!$C$2:$C$11",
        })
        chart_prod.set_title({"name": "Top Products by Revenue"})
        chart_prod.set_y_axis({"major_gridlines": {"visible": False}})
        dash.insert_chart("D20", chart_prod, {"x_scale": 1.4, "y_scale": 1.2})

        # 3) Revenue by Segment/Channel (SegmentChannel!A:D)
        chart_sc = wb.add_chart({"type": "bar"})
        # Build categories as "Segment - Channel"
        # We'll write a helper table on the dashboard for combined labels
        dash.write("A12", "Segment-Channel", kpi_label)
        dash.write("B12", "Revenue", kpi_label)

        # Pull up to first 10 rows for the bar chart
        sc_df = kpis["by_channel"].head(10).copy()
        # Write helper table at A13
        start_row = 12
        for i, row in sc_df.reset_index(drop=True).iterrows():
            dash.write(start_row + 1 + i, 0, f"{row['segment']} - {row['channel']}")
            dash.write(start_row + 1 + i, 1, row["revenue"])

        last_row = start_row + 1 + len(sc_df)
        chart_sc.add_series({
            "name":       "Revenue",
            "categories": f"=Dashboard!$A$13:$A${last_row}",
            "values":     f"=Dashboard!$B$13:$B${last_row}",
        })
        chart_sc.set_title({"name": "Revenue by Segment/Channel"})
        chart_sc.set_y_axis({"major_gridlines": {"visible": False}})
        dash.insert_chart("A20", chart_sc, {"x_scale": 1.2, "y_scale": 1.2})

def write_html(kpis: dict) -> None:
    # Simple, readable HTML summary
    style = """
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
      h1 { margin-bottom: 0; }
      .muted { color: #666; margin-top: 4px; }
      .kpis { display: grid; grid-template-columns: repeat(5, minmax(140px, 1fr)); gap: 12px; margin: 20px 0; }
      .card { border: 1px solid #e5e5e5; border-radius: 10px; padding: 12px; }
      .label { font-weight: 600; font-size: 12px; color: #555; }
      .value { font-size: 18px; margin-top: 6px; }
      table { border-collapse: collapse; width: 100%; margin: 20px 0; }
      th, td { border: 1px solid #eee; padding: 8px 10px; text-align: left; }
      th { background: #fafafa; }
      .section-title { margin-top: 28px; }
    </style>
    """

    def money(x: float) -> str:
        try:
            return f"${x:,.0f}"
        except Exception:
            return str(x)

    html = f"""
    <html>
    <head><meta charset="utf-8"><title>Sales Summary</title>{style}</head>
    <body>
      <h1>Sales & Transaction Summary</h1>
      <div class="muted">Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>

      <div class="kpis">
        <div class="card"><div class="label">Total Revenue</div><div class="value">{money(kpis['total_revenue'])}</div></div>
        <div class="card"><div class="label">Orders</div><div class="value">{kpis['orders']:,}</div></div>
        <div class="card"><div class="label">Customers</div><div class="value">{kpis['customers']:,}</div></div>
        <div class="card"><div class="label">AOV</div><div class="value">{money(kpis['aov'])}</div></div>
        <div class="card"><div class="label">Repeat Order Rate</div><div class="value">{kpis['repeat_order_rate']:.1%}</div></div>
      </div>

      <h2 class="section-title">Revenue by Month</h2>
      {kpis['monthly'].to_html(index=False)}

      <h2 class="section-title">Top Products</h2>
      {kpis['top_products'].to_html(index=False)}

      <h2 class="section-title">Revenue by Segment & Channel</h2>
      {kpis['by_channel'].to_html(index=False)}
    </body>
    </html>
    """
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)

def main() -> None:
    ensure_dirs()
    seed_sample_data()
    customers, txns = load_data()
    kpis = compute_kpis(customers, txns)
    write_excel(kpis)
    write_html(kpis)
    print(f"Done.\n- Excel:  {EXCEL_OUT}\n- HTML:   {HTML_OUT}")

if __name__ == "__main__":
    main()
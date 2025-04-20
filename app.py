import os
import io
from flask import Flask, request, send_file, jsonify
from weasyprint import HTML
import pandas as pd
from datetime import datetime, date
from collections import defaultdict

app = Flask(__name__)

@app.route('/')
def index():
    return open("index.html", encoding="utf-8").read()

@app.route("/upload", methods=["POST"])
def upload_invoice():
    from_name = request.form.get("from_name", "")
    to_name = request.form.get("to_name", "")
    invoice_number = request.form.get("invoice_number", "")
    invoice_date = request.form.get("invoice_date", "")
    due_date = request.form.get("due_date", "")
    base_currency = request.form.get("base_currency", "")
    bank_details = request.form.get("bank_details", "")
    notes = request.form.get("notes", "")
    workdays = list(map(int, request.form.getlist("workdays")))

    try:
        hourly_rate = float(request.form.get("hourly_rate", "0") or "0")
    except ValueError:
        hourly_rate = 0.0

    try:
        goal_amount = float(request.form.get("goal_amount", "0") or "0")
    except ValueError:
        goal_amount = 0.0

    uploaded_file = request.files["clockify_csv"]
    df = pd.read_csv(uploaded_file)

    total_hours = df["Duration (decimal)"].sum()

    # Detect actual worked days from available date fields
    date_fields = ["Start date", "Start time", "Date", "Start"]
    for field in date_fields:
        if field in df.columns:
            try:
                days_worked = pd.to_datetime(df[field], errors='coerce').dt.date.nunique()
                break
            except:
                days_worked = 0
    else:
        days_worked = 0

    avg_hours_per_day = total_hours / days_worked if days_worked else 0

    today = date.today()
    end_of_month = pd.Timestamp(today).replace(day=28) + pd.offsets.MonthEnd(0)
    calendar_range = pd.date_range(start=today, end=end_of_month)
    remaining_workdays = sum(1 for d in calendar_range if d.weekday() in workdays)

    income_so_far = round(total_hours * hourly_rate, 2)
    remaining_amount = max(0, goal_amount - income_so_far)
    needed_hours = remaining_amount / hourly_rate if hourly_rate else 0
    needed_avg = needed_hours / remaining_workdays if remaining_workdays else 0

    # Group by project
    project_hours = df.groupby("Project")["Duration (decimal)"].sum().to_dict()
    breakdown_html = ''.join(f"<li>{p or 'Unassigned'}: {h:.2f} hrs</li>" for p, h in project_hours.items())

    table_rows = ''.join(
        f"<tr><td>{r.get('Project', '')}</td><td>{r.get('Description', '')}</td><td>{r.get('Duration (decimal)', 0):.2f}</td></tr>"
        for _, r in df.iterrows()
    )

    buffer = io.BytesIO()
    HTML(string=f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial; padding: 30px; }}
        h1 {{ color: #0052cc; }}
        .right {{ float: right; text-align: right; }}
        .split {{ display: flex; justify-content: space-between; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; }}
        th {{ background: #f0f4ff; }}
        td:nth-child(2) {{ word-break: break-word; }}
      </style>
    </head>
    <body>
      <div class="split">
        <div>
          <h2>Invoice</h2>
          <p><strong>From:</strong> {from_name}<br>
          <strong>To:</strong> {to_name}<br>
          <strong>Invoice #:</strong> {invoice_number}<br>
          <strong>Invoice Date:</strong> {invoice_date}<br>
          <strong>Due Date:</strong> {due_date}</p>
        </div>
        <div class="right">
          <p><strong>Bank Details:</strong><br>{bank_details.replace('\n', '<br>')}</p>
          <p><strong>Total Hours:</strong> {total_hours:.2f} hrs<br>
          <strong>Total Amount:</strong> {income_so_far:.2f} {base_currency}</p>
        </div>
      </div>

      <h3>Project Breakdown</h3>
      <ul>{breakdown_html}</ul>

      <table>
        <thead>
          <tr>
            <th>Project</th>
            <th>Description</th>
            <th>Hours</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
      <p><em>{notes}</em></p>
    </body>
    </html>
    """).write_pdf(buffer)
    buffer.seek(0)

    return send_file(buffer, mimetype="application/pdf", as_attachment=False)

@app.route("/summary", methods=["POST"])
def summary():
    try:
        hourly_rate = float(request.form.get("hourly_rate", "0") or "0")
    except ValueError:
        hourly_rate = 0.0

    try:
        goal_amount = float(request.form.get("goal_amount", "0") or "0")
    except ValueError:
        goal_amount = 0.0

    workdays = list(map(int, request.form.getlist("workdays")))
    uploaded_file = request.files["clockify_csv"]
    df = pd.read_csv(uploaded_file)

    total_hours = df["Duration (decimal)"].sum()

    date_fields = ["Start date", "Start time", "Date", "Start"]
    for field in date_fields:
        if field in df.columns:
            try:
                days_worked = pd.to_datetime(df[field], errors='coerce').dt.date.nunique()
                break
            except:
                days_worked = 0
    else:
        days_worked = 0

    avg_hours_per_day = total_hours / days_worked if days_worked else 0

    today = date.today()
    end_of_month = pd.Timestamp(today).replace(day=28) + pd.offsets.MonthEnd(0)
    calendar_range = pd.date_range(start=today, end=end_of_month)
    remaining_days = sum(1 for d in calendar_range if d.weekday() in workdays)

    income_so_far = round(total_hours * hourly_rate, 2)
    projected_income = round(income_so_far + (avg_hours_per_day * remaining_days * hourly_rate), 2)

    remaining_amount = max(0, goal_amount - income_so_far)
    needed_hours = remaining_amount / hourly_rate if hourly_rate else 0
    needed_avg = needed_hours / remaining_days if remaining_days else 0

    return jsonify({
        "income_so_far": income_so_far,
        "projected_income": projected_income,
        "remaining_days": remaining_days,
        "needed_avg_hours_per_day": round(needed_avg, 2)
    })

if __name__ == "__main__":
    app.run(debug=True)

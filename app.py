from flask import Flask, render_template, request, send_file, jsonify
from weasyprint import HTML
import pandas as pd
from io import BytesIO
import calendar
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

# In-memory storage
csv_data = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_invoice():
    global csv_data

    csv_file = request.files["csv_file"]
    df = pd.read_csv(csv_file)

    from_name = request.form.get("from_name", "")
    to_name = request.form.get("to_name", "")
    invoice_number = request.form.get("invoice_number", "")
    invoice_date = request.form.get("invoice_date", "")
    due_date = request.form.get("due_date", "")
    hourly_rate = float(request.form.get("hourly_rate", 0) or 0)
    base_currency = request.form.get("base_currency", "")
    bank_details = request.form.get("bank_details", "")
    notes = request.form.get("notes", "")
    goal_amount = float(request.form.get("goal_amount", 0) or 0)
    workdays = list(map(int, request.form.getlist("workdays")))

    df["Duration (h)"] = pd.to_timedelta(df["Duration"]).dt.total_seconds() / 3600

    # Store data in memory
    csv_data = {
        "df": df,
        "from_name": from_name,
        "to_name": to_name,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "hourly_rate": hourly_rate,
        "base_currency": base_currency,
        "bank_details": bank_details,
        "notes": notes,
        "goal_amount": goal_amount,
        "workdays": workdays,
    }

    buffer = BytesIO()
    generate_invoice_pdf(buffer, csv_data)
    buffer.seek(0)

    return send_file(buffer, mimetype="application/pdf")

@app.route("/summary", methods=["POST"])
def summary():
    global csv_data
    if not csv_data:
        return jsonify({"error": "No data available"}), 400

    df = csv_data["df"]
    hourly_rate = csv_data["hourly_rate"]
    goal_amount = csv_data["goal_amount"]
    workdays = csv_data["workdays"]

    df["Start date"] = pd.to_datetime(df["Start"])
    df["Work day"] = df["Start date"].dt.weekday
    df = df[df["Work day"].isin(workdays)]

    now = datetime.now()
    month_start = now.replace(day=1)
    next_month = month_start + timedelta(days=32)
    month_end = next_month.replace(day=1) - timedelta(days=1)

    remaining_days = [
        month_start + timedelta(days=i)
        for i in range((month_end - month_start).days + 1)
        if (month_start + timedelta(days=i)).weekday() in workdays and
        (month_start + timedelta(days=i)).date() >= now.date()
    ]

    remaining_workdays = len(remaining_days)
    total_hours = df["Duration (h)"].sum()
    earned_so_far = total_hours * hourly_rate
    remaining_goal = max(goal_amount - earned_so_far, 0)
    required_hours = remaining_goal / hourly_rate if hourly_rate else 0
    avg_hours_per_day = required_hours / remaining_workdays if remaining_workdays else 0
    avg_hours_so_far = total_hours / df["Start date"].dt.date.nunique()

    return jsonify({
        "earned_so_far": round(earned_so_far, 2),
        "remaining_goal": round(remaining_goal, 2),
        "required_hours": round(required_hours, 2),
        "avg_hours_per_day": round(avg_hours_per_day, 2),
        "avg_hours_so_far": round(avg_hours_so_far, 2),
        "remaining_workdays": remaining_workdays,
        "total_hours": round(total_hours, 2)
    })

def generate_invoice_pdf(buffer, data):
    df = data["df"]
    from_name = data["from_name"]
    to_name = data["to_name"]
    invoice_number = data["invoice_number"]
    invoice_date = data["invoice_date"]
    due_date = data["due_date"]
    hourly_rate = data["hourly_rate"]
    base_currency = data["base_currency"]
    bank_details = data["bank_details"]
    notes = data["notes"]

    df["Duration (h)"] = pd.to_timedelta(df["Duration"]).dt.total_seconds() / 3600
    df["Amount"] = df["Duration (h)"] * hourly_rate

    rows = df[["Project", "Description", "Start", "Duration (h)", "Amount"]].values
    rows_html = "\n".join(
        f"<tr><td>{project}</td><td>{desc}</td><td>{start}</td><td>{hours:.2f}</td><td>{base_currency} {amount:.2f}</td></tr>"
        for project, desc, start, hours, amount in rows
    )

    total_amount = df["Amount"].sum()

    # Escape line breaks for HTML
    bank_details_html = bank_details.replace('\n', '<br>')
    notes_html = notes.replace('\n', '<br>')

    html_template = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 12px; }}
            h1 {{ text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #000; padding: 5px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Invoice</h1>
        <p><strong>From:</strong> {from_name}</p>
        <p><strong>To:</strong> {to_name}</p>
        <p><strong>Invoice Number:</strong> {invoice_number}</p>
        <p><strong>Invoice Date:</strong> {invoice_date}</p>
        <p><strong>Due Date:</strong> {due_date}</p>
        <table>
            <tr>
                <th>Project</th>
                <th>Description</th>
                <th>Start</th>
                <th>Hours</th>
                <th>Amount</th>
            </tr>
            {rows_html}
        </table>
        <h2>Total: {base_currency} {total_amount:.2f}</h2>
        <div><strong>Bank Details:</strong><br>{bank_details_html}</div>
        <br>
        <div><strong>Notes:</strong><br>{notes_html}</div>
    </body>
    </html>
    """

    HTML(string=html_template).write_pdf(buffer)

if __name__ == "__main__":
    app.run(debug=True)

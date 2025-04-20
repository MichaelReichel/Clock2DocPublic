from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
from datetime import datetime
import os
import io
from weasyprint import HTML
from collections import defaultdict

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summary', methods=['POST'])
def summary():
    try:
        file = request.files['csv_file']
        if not file:
            return jsonify({'error': 'No file provided'}), 400

        df = pd.read_csv(file)
        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        df = df.dropna(subset=['Start Date'])

        df['Date Only'] = df['Start Date'].dt.date
        df['Duration (decimal)'] = pd.to_numeric(df['Duration (decimal)'], errors='coerce')
        df = df.dropna(subset=['Duration (decimal)'])

        total_hours = df['Duration (decimal)'].sum()
        days_worked = df['Date Only'].nunique()

        return jsonify({
            'total_hours': round(total_hours, 2),
            'days_worked': days_worked
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_invoice():
    try:
        csv_file = request.files['csv_file']
        logo_file = request.files.get('logo_file')
        from_name = request.form.get("from_name", "")
        to_name = request.form.get("to_name", "")
        invoice_number = request.form.get("invoice_number", "")
        invoice_date = request.form.get("invoice_date", datetime.today().strftime('%Y-%m-%d'))
        due_date = request.form.get("due_date", "")
        hourly_rate = float(request.form.get("hourly_rate", 0))
        base_currency = request.form.get("base_currency", "")
        bank_details = request.form.get("bank_details", "")
        notes = request.form.get("notes", "")
        goal_amount = float(request.form.get("goal_amount", 0))
        workdays = list(map(int, request.form.getlist("workdays")))
        theme = request.form.get("theme", "default")
        orientation = request.form.get("orientation", "portrait")
        output_format = request.form.get("output_format", "pdf")

        df = pd.read_csv(csv_file)
        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        df = df.dropna(subset=['Start Date'])
        df['Date Only'] = df['Start Date'].dt.date
        df['Duration (decimal)'] = pd.to_numeric(df['Duration (decimal)'], errors='coerce')
        df = df.dropna(subset=['Duration (decimal)'])

        total_hours = df['Duration (decimal)'].sum()
        total_amount = total_hours * hourly_rate
        days_worked = df['Date Only'].nunique()

        remaining_days = len([d for d in df['Date Only'].unique() if d >= datetime.today().date()])
        remaining_days = max(1, remaining_days if workdays else 1)

        hours_left = max(goal_amount - total_amount, 0) / hourly_rate
        average_hours_needed = hours_left / remaining_days if remaining_days > 0 else 0

        project_hours = defaultdict(float)
        if 'Project' in df.columns:
            for _, row in df.iterrows():
                project_hours[row['Project']] += row['Duration (decimal)']

        table_rows = ""
        for _, row in df.iterrows():
            desc = row.get("Description", "")
            duration = row["Duration (decimal)"]
            amount = round(duration * hourly_rate, 2)
            table_rows += f"""
                <tr>
                    <td>{desc}</td>
                    <td>{duration:.2f}</td>
                    <td>{base_currency} {amount:.2f}</td>
                </tr>
            """

        project_summary = "".join(
            f"<div><strong>{proj}</strong>: {round(hours, 2)} hrs</div>"
            for proj, hours in project_hours.items()
        )

        summary_panel = f"""
            <div>
                <strong>Total Hours:</strong> {round(total_hours, 2)}<br>
                <strong>Days Worked:</strong> {days_worked}<br>
                <strong>Remaining Work Days:</strong> {remaining_days}<br>
                <strong>Total Amount:</strong> {base_currency} {round(total_amount, 2)}<br>
                <strong>Hours Needed to Reach Goal:</strong> {round(hours_left, 2)}<br>
                <strong>Daily Average Needed:</strong> {round(average_hours_needed, 2)}<br>
            </div>
        """

        html_template = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 30px;
                }}
                .top {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 40px;
                }}
                .table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 40px;
                }}
                .table th, .table td {{
                    border: 1px solid #ccc;
                    padding: 10px;
                    word-wrap: break-word;
                    max-width: 200px;
                }}
                .right {{
                    text-align: right;
                }}
                .title {{
                    font-size: 28px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .summary {{
                    margin-top: 40px;
                }}
            </style>
        </head>
        <body>
            <div class="top">
                <div>
                    <div class="title">Invoice</div>
                    <div><strong>From:</strong> {from_name}</div>
                    <div><strong>To:</strong> {to_name}</div>
                    <div><strong>Invoice Date:</strong> {invoice_date}</div>
                    <div><strong>Due Date:</strong> {due_date}</div>
                    {project_summary}
                </div>
                <div class="right">
                    <div><strong>Invoice #:</strong> {invoice_number}</div>
                    <div><strong>Bank Details:</strong><br>{bank_details.replace('\n', '<br>')}</div>
                </div>
            </div>
            <table class="table">
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Hours</th>
                        <th>Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            <div class="summary">
                <strong>Notes:</strong><br>{notes.replace('\n', '<br>')}
            </div>
        </body>
        </html>
        """

        buffer = io.BytesIO()
        HTML(string=html_template).write_pdf(buffer)
        buffer.seek(0)

        return send_file(buffer, download_name="invoice.pdf", as_attachment=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

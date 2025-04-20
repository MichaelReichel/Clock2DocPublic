from flask import Flask, render_template, request, send_file, jsonify, make_response
import pandas as pd
from datetime import datetime
from weasyprint import HTML
from jinja2 import Template
import os
import io

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
        action = request.form.get("action", "download")
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

        df = pd.read_csv(csv_file)
        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        df = df.dropna(subset=['Start Date'])

        df['Date Only'] = df['Start Date'].dt.date
        df['Duration (decimal)'] = pd.to_numeric(df['Duration (decimal)'], errors='coerce')
        df = df.dropna(subset=['Duration (decimal)'])

        total_hours = df['Duration (decimal)'].sum()
        total_amount = total_hours * hourly_rate

        # HTML template for PDF
        html_template = Template("""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h1>Invoice</h1>
            <p><strong>From:</strong> {{ from_name }}</p>
            <p><strong>To:</strong> {{ to_name }}</p>
            <p><strong>Invoice Number:</strong> {{ invoice_number }}</p>
            <p><strong>Date:</strong> {{ invoice_date }}</p>
            <p><strong>Due Date:</strong> {{ due_date }}</p>
            <hr>
            <h3>Summary</h3>
            <p>Total Hours: {{ total_hours }} hours</p>
            <p>Hourly Rate: {{ hourly_rate }} {{ base_currency }}</p>
            <p><strong>Total Amount:</strong> {{ total_amount }} {{ base_currency }}</p>
            <hr>
            <h4>Bank Details</h4>
            <p>{{ bank_details }}</p>
            <h4>Notes</h4>
            <p>{{ notes }}</p>
        </body>
        </html>
        """)

        html_content = html_template.render(
            from_name=from_name,
            to_name=to_name,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=due_date,
            hourly_rate=hourly_rate,
            total_hours=round(total_hours, 2),
            total_amount=round(total_amount, 2),
            base_currency=base_currency,
            bank_details=bank_details.replace('\n', '<br>'),
            notes=notes
        )

        pdf = HTML(string=html_content).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        if action == "download":
            response.headers['Content-Disposition'] = 'attachment; filename=invoice.pdf'
        else:
            response.headers['Content-Disposition'] = 'inline; filename=invoice.pdf'
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

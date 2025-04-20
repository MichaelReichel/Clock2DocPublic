from flask import Flask, render_template, request, send_file
import pandas as pd
from io import BytesIO
from weasyprint import HTML
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_invoice():
    try:
        file = request.files["csvFile"]
        company_name = request.form.get("companyName", "")
        company_address = request.form.get("companyAddress", "")
        client_name = request.form.get("clientName", "")
        client_address = request.form.get("clientAddress", "")
        hourly_rate = float(request.form.get("hourlyRate", "0"))
        invoice_number = request.form.get("invoiceNumber", "")
        invoice_date = request.form.get("invoiceDate", "")
        due_date = request.form.get("dueDate", "")
        bank_details = request.form.get("bankDetails", "")
        earnings_goal = request.form.get("earningsGoal", "")
        working_days = request.form.getlist("workingDays")

        if not file:
            return "No file uploaded", 400

        df = pd.read_csv(file)

        # Fix for CSVs with different column names
        if "Duration" in df.columns:
            duration_col = "Duration"
        elif "Duration (h)" in df.columns:
            duration_col = "Duration (h)"
        else:
            return "CSV is missing a 'Duration' or 'Duration (h)' column.", 400

        if duration_col == "Duration":
            df["Duration (h)"] = pd.to_timedelta(df["Duration"]).dt.total_seconds() / 3600
        else:
            df["Duration (h)"] = df[duration_col]

        grouped = df.groupby("Project")["Duration (h)"].sum().reset_index()
        grouped["Amount"] = grouped["Duration (h)"] * hourly_rate

        total_hours = grouped["Duration (h)"].sum()
        total_amount = grouped["Amount"].sum()

        buffer = BytesIO()
        html = HTML(string=f"""
            <h1>Invoice</h1>
            <p><strong>Invoice Number:</strong> {invoice_number}</p>
            <p><strong>Invoice Date:</strong> {invoice_date}</p>
            <p><strong>Due Date:</strong> {due_date}</p>
            <p><strong>Company:</strong> {company_name}</p>
            <p>{company_address.replace('\n', '<br>')}</p>
            <p><strong>Client:</strong> {client_name}</p>
            <p>{client_address.replace('\n', '<br>')}</p>
            <hr>
            <table style="width:100%; border-collapse: collapse;" border="1" cellpadding="6">
                <thead>
                    <tr>
                        <th>Project</th>
                        <th>Hours</th>
                        <th>Rate</th>
                        <th>Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f"<tr><td>{row['Project']}</td><td>{row['Duration (h)']:.2f}</td><td>£{hourly_rate:.2f}</td><td>£{row['Amount']:.2f}</td></tr>" for _, row in grouped.iterrows()])}
                </tbody>
            </table>
            <h3>Total: £{total_amount:.2f}</h3>
            <hr>
            <p><strong>Bank Details:</strong><br>{bank_details.replace('\n', '<br>')}</p>
        """)
        html.write_pdf(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=False,
            download_name=f"invoice_{invoice_number}.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        return str(e), 500

@app.route("/summary", methods=["POST"])
def summary():
    return "Summary placeholder", 200

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request, send_file
import pandas as pd
from io import BytesIO
from weasyprint import HTML
import os

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_invoice():
    try:
        file = request.files["csvFile"]
        if not file:
            return "No file uploaded", 400

        # Extract form data
        form = request.form
        company_name = form.get("companyName", "")
        company_address = form.get("companyAddress", "").replace("\n", "<br>")
        client_name = form.get("clientName", "")
        client_address = form.get("clientAddress", "").replace("\n", "<br>")
        hourly_rate = float(form.get("hourlyRate", "0"))
        invoice_number = form.get("invoiceNumber", "")
        invoice_date = form.get("invoiceDate", "")
        due_date = form.get("dueDate", "")
        bank_details = form.get("bankDetails", "").replace("\n", "<br>")

        # Read CSV
        df = pd.read_csv(file)

        if "Duration" in df.columns:
            df["Duration (h)"] = pd.to_timedelta(df["Duration"]).dt.total_seconds() / 3600
        elif "Duration (h)" in df.columns:
            df["Duration (h)"] = df["Duration (h)"]
        else:
            return "CSV missing 'Duration' or 'Duration (h)' column.", 400

        grouped = df.groupby("Project")["Duration (h)"].sum().reset_index()
        grouped["Amount"] = grouped["Duration (h)"] * hourly_rate

        total_amount = grouped["Amount"].sum()

        rows_html = "".join(
            f"<tr><td>{row['Project']}</td><td>{row['Duration (h)']:.2f}</td><td>£{hourly_rate:.2f}</td><td>£{row['Amount']:.2f}</td></tr>"
            for _, row in grouped.iterrows()
        )

        invoice_html = f"""
        <h1>Invoice</h1>
        <p><strong>Invoice Number:</strong> {invoice_number}</p>
        <p><strong>Invoice Date:</strong> {invoice_date}</p>
        <p><strong>Due Date:</strong> {due_date}</p>
        <p><strong>Company:</strong> {company_name}</p>
        <p>{company_address}</p>
        <p><strong>Client:</strong> {client_name}</p>
        <p>{client_address}</p>
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
                {rows_html}
            </tbody>
        </table>
        <h3>Total: £{total_amount:.2f}</h3>
        <hr>
        <p><strong>Bank Details:</strong><br>{bank_details}</p>
        """

        buffer = BytesIO()
        HTML(string=invoice_html).write_pdf(buffer)
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

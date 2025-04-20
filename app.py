import os
from flask import Flask, render_template, request, send_file
import pandas as pd
from weasyprint import HTML
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

def parse_duration_column(df):
    # Handle multiple possible column names from Clockify
    if "Duration (h)" in df.columns:
        df["Hours"] = pd.to_timedelta(df["Duration (h)"])
        df["Hours"] = df["Hours"].dt.total_seconds() / 3600
    elif "Duration" in df.columns:
        df["Hours"] = pd.to_timedelta(df["Duration"]).dt.total_seconds() / 3600
    elif "Time (h)" in df.columns:
        df["Hours"] = pd.to_numeric(df["Time (h)"], errors="coerce")
    else:
        raise ValueError("No valid duration column found.")
    return df

@app.route("/upload", methods=["POST"])
def upload_invoice():
    try:
        file = request.files["csv_file"]
        if not file:
            return "No CSV uploaded", 400

        df = pd.read_csv(file)
        df = parse_duration_column(df)

        business = request.form.get("business_name", "")
        client = request.form.get("client_name", "")
        invoice_number = request.form.get("invoice_number", "")
        hourly_rate = float(request.form.get("hourly_rate", 0))

        df["Amount"] = df["Hours"] * hourly_rate
        total_amount = df["Amount"].sum()
        date_str = datetime.today().strftime("%Y-%m-%d")

        # Optional logo
        logo_path = ""
        if "logo_file" in request.files and request.files["logo_file"].filename != "":
            logo = request.files["logo_file"]
            logo_filename = secure_filename(logo.filename)
            logo_path = os.path.join(UPLOAD_FOLDER, logo_filename)
            logo.save(logo_path)

        html = render_template("invoice_template.html",
                               business=business,
                               client=client,
                               invoice_number=invoice_number,
                               date=date_str,
                               entries=df.to_dict(orient="records"),
                               total="{:.2f}".format(total_amount),
                               logo_path=logo_path)

        pdf_path = os.path.join(UPLOAD_FOLDER, "invoice_preview.pdf")
        HTML(string=html).write_pdf(pdf_path)
        return send_file(pdf_path, mimetype="application/pdf")

    except Exception as e:
        return f"Error generating invoice: {e}", 500

@app.route("/download", methods=["POST"])
def download_invoice():
    return upload_invoice()

if __name__ == "__main__":
    app.run(debug=True)

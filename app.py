from flask import Flask, request, jsonify

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import extract_text_from_docx, split_invoices
from extractor import extract_invoice_fields


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)


@app.route("/extract-invoices", methods=["POST"])
def extract_invoices():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Extract full text from the uploaded .docx
    text = extract_text_from_docx(filepath)

    # Split into individual invoice chunks
    invoice_chunks = split_invoices(text)

    # Extract structured fields from each invoice
    results = []
    for chunk in invoice_chunks:
        extracted = extract_invoice_fields(chunk)
        results.append(extracted)

    return jsonify({"invoices": results}), 200


# BUG FIX: app.run() was incorrectly placed inside the route handler.
# It must be at the module level so it only runs when the script is executed directly.
if __name__ == "__main__":
    app.run(debug=True)
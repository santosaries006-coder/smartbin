import os
import json
from flask import Flask, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

APP = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
BINS_FILE = os.path.join(BASE_DIR, "bins.json")

# Load bins mapping
with open(BINS_FILE, "r") as f:
    BINS = json.load(f)

# SMTP config from env
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.mailtrap.io")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "no-reply@smartbin.example")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")


def send_email(to_email, subject, html_body, text_body=None):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    if text_body is None:
        text_body = html_body

    part1 = MIMEText(text_body, "plain")
    part2 = MIMEText(html_body, "html")
    msg.attach(part1)
    msg.attach(part2)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        if SMTP_USER and SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(FROM_EMAIL, [to_email], msg.as_string())


@APP.route("/api/bin-status", methods=["POST"])
def bin_status():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "invalid json"}), 400

    bin_id = data.get("bin_id")
    status = data.get("status")
    fill_level = data.get("fill_level")

    if not bin_id or status is None:
        return jsonify({"error": "missing bin_id or status"}), 400

    # Lookup bin
    bin_info = BINS.get(bin_id)
    if not bin_info:
        return jsonify({"error": f"unknown bin_id: {bin_id}"}), 404

    # Only act on FULL status (for this flow)
    if status.upper() == "FULL":
        subject = f"Smart Bin Alert: {bin_info['name']} is FULL"
        html_body = f"""
        <h3>Smart Bin Alert</h3>
        <ul>
          <li><strong>Bin:</strong> {bin_info['name']}</li>
          <li><strong>Location:</strong> {bin_info['location']}</li>
          <li><strong>Status:</strong> FULL</li>
          <li><strong>Fill Level:</strong> {fill_level}%</li>
        </ul>
        <p><strong>Notification:</strong> The Smart Bin at this location is already full and needs to be collected.</p>
        """
        text_body = (f"Smart Bin Alert\n\n"
                     f"Bin: {bin_info['name']}\n"
                     f"Location: {bin_info['location']}\n"
                     f"Status: FULL\n"
                     f"Fill Level: {fill_level}%\n\n"
                     "Notification: The Smart Bin at this location is already full and needs to be collected.\n")

        # send to user
        user_email = bin_info.get("user_email")
        if user_email:
            try:
                send_email(user_email, subject, html_body, text_body)
            except Exception as e:
                return jsonify({"error": "failed sending user email", "detail": str(e)}), 500

        # send to admin
        try:
            send_email(ADMIN_EMAIL, subject, html_body, text_body)
        except Exception as e:
            return jsonify({"error": "failed sending admin email", "detail": str(e)}), 500

        return jsonify({"result": "emails_sent", "bin": bin_id}), 200

    return jsonify({"result": "no_action", "reason": "status_not_full"}), 200


if __name__ == "__main__":
    APP.run(host="0.0.0.0", port=5000, debug=True)

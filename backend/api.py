import os
import smtplib
from email.message import EmailMessage
from email.headerregistry import Address

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://127.0.0.1:5500",
            "http://localhost:5500",
        ]
    }
})


@app.post("/api/contact")
def contact():
    if not request.is_json:
        return jsonify(error="Permintaan harus berupa JSON."), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Data formulir tidak valid."), 400

    name = data.get("name")
    sender = data.get("email")
    message = data.get("message")
    if not all(isinstance(value, str) for value in (name, sender, message)):
        return jsonify(error="Periksa kembali isi formulir."), 400

    name = name.strip()
    sender = sender.strip()
    message = message.strip()
    try:
        Address(addr_spec=sender)
        valid_sender = (
            len(sender) <= 254
            and "\n" not in sender
            and "\r" not in sender
        )
    except ValueError:
        valid_sender = False

    if (
        not name
        or len(name) > 100
        or "\n" in name
        or "\r" in name
        or not valid_sender
        or not message
        or len(message) > 5000
    ):
        return jsonify(error="Periksa kembali isi formulir."), 400

    gmail_address = os.environ.get("GMAIL_ADDRESS", "").strip()
    gmail_password = os.environ.get("GMAIL_PASSWORD", "").replace(" ", "")
    contact_email = os.environ.get("CONTACT_EMAIL", "").strip()
    if not all((gmail_address, gmail_password, contact_email)):
        app.logger.error("Konfigurasi Gmail belum lengkap di backend/.env")
        return jsonify(error="Server email belum dikonfigurasi."), 503

    try:
        gmail_from = Address(addr_spec=gmail_address)
        recipient = Address(addr_spec=contact_email)
    except ValueError:
        app.logger.error("Alamat email di konfigurasi backend tidak valid")
        return jsonify(error="Konfigurasi alamat email server tidak valid."), 503

    email = EmailMessage()
    email["Subject"] = f"Pesan dari website: {name}"
    email["From"] = gmail_from
    email["To"] = recipient
    email["Reply-To"] = sender
    email.set_content(f"Nama: {name}\nEmail: {sender}\n\n{message}")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(gmail_address, gmail_password)
            smtp.send_message(email)
    except (OSError, smtplib.SMTPException):
        app.logger.exception("Gagal mengirim pesan kontak")
        return jsonify(error="Pesan belum berhasil dikirim. Coba lagi nanti."), 502

    return jsonify(message="Pesan berhasil dikirim.")
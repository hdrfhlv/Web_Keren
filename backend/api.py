import base64
import os
from email.headerregistry import Address
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from httplib2 import HttpLib2Error

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / "token.json"
CREDENTIALS_FILE = BASE_DIR.parent / "Oauth.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://127.0.0.1:5500",
                "http://localhost:5500",
            ]
        }
    },
)


def create_gmail_service():
    if not CREDENTIALS_FILE.is_file():
        raise FileNotFoundError(
            f"OAuth client credentials not found: {CREDENTIALS_FILE.name}"
        )
    if not TOKEN_FILE.is_file():
        raise FileNotFoundError(
            f"Gmail OAuth token not found: {TOKEN_FILE.name}"
        )

    credentials = Credentials.from_authorized_user_file(
        str(TOKEN_FILE),
        SCOPES,
    )
    if credentials.expired:
        if not credentials.refresh_token:
            raise ValueError("OAuth token cannot be refreshed.")
        credentials.refresh(Request())
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    if not credentials.valid:
        raise ValueError("Gmail OAuth credentials are invalid.")

    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


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
        sender_address = Address(addr_spec=sender)
        valid_sender = len(sender) <= 254
    except ValueError:
        sender_address = None
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
    contact_email = os.environ.get("CONTACT_EMAIL", "").strip()
    if not gmail_address or not contact_email:
        app.logger.error(
            "GMAIL_ADDRESS dan CONTACT_EMAIL harus dikonfigurasi di backend/.env"
        )
        return jsonify(error="Konfigurasi alamat email server belum lengkap."), 503

    try:
        sender_identity = Address(addr_spec=gmail_address)
        recipient = Address(addr_spec=contact_email)
    except ValueError:
        app.logger.error("Alamat email pada konfigurasi backend tidak valid")
        return jsonify(error="Alamat email server tidak valid."), 503

    email = EmailMessage()
    email["From"] = sender_identity
    email["Subject"] = f"Pesan dari website: {name}"
    email["To"] = recipient
    email["Reply-To"] = sender_address
    email.set_content(f"Nama: {name}\nEmail: {sender}\n\n{message}")
    raw_message = base64.urlsafe_b64encode(email.as_bytes()).decode("ascii")

    try:
        service = create_gmail_service()
    except FileNotFoundError:
        app.logger.exception("File konfigurasi OAuth Gmail belum tersedia")
        return jsonify(error="Server email belum diotorisasi. Ikuti panduan setup Gmail API."), 503
    except (GoogleAuthError, OSError, ValueError):
        app.logger.exception("Gagal memuat kredensial OAuth Gmail")
        return jsonify(error="Autentikasi Gmail gagal. Otorisasi ulang akun email."), 503

    try:
        (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )
    except (HttpError, HttpLib2Error, OSError):
        app.logger.exception("Gmail API gagal mengirim pesan kontak")
        return jsonify(error="Pesan belum berhasil dikirim. Coba lagi nanti."), 502

    return jsonify(message="Pesan berhasil dikirim.")

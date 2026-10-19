from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR.parent / "Oauth.json"
TOKEN_FILE = BASE_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
    if not CREDENTIALS_FILE.is_file():
        raise SystemExit(
            "Download the OAuth Desktop app JSON from Google Cloud Console "
            f"and save it as {CREDENTIALS_FILE}."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        SCOPES,
    )
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        access_type="offline",
        prompt="consent",
    )
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
    print(f"Gmail authorization saved to {TOKEN_FILE.name}.")


if __name__ == "__main__":
    main()

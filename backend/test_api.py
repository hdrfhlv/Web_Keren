import os
import base64
from email import message_from_bytes
import unittest
from unittest.mock import patch

import api


class ContactEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = api.app.test_client()
        self.settings = patch.dict(
            os.environ,
            {
                "GMAIL_ADDRESS": "sender@example.com",
                "CONTACT_EMAIL": "recipient@example.com",
            },
        )
        self.settings.start()
        self.addCleanup(self.settings.stop)

    def test_rejects_invalid_form(self):
        response = self.client.post("/api/contact", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_rejects_non_json_request(self):
        response = self.client.post("/api/contact", data="not json")

        self.assertEqual(response.status_code, 400)

    @patch("api.create_gmail_service")
    def test_sends_contact_email_with_gmail_api(self, create_service):
        service = create_service.return_value
        response = self.client.post(
            "/api/contact",
            json={
                "name": "Test User",
                "email": "visitor@example.com",
                "message": "Please contact me.",
            },
        )

        self.assertEqual(response.status_code, 200)
        send = service.users.return_value.messages.return_value.send
        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["userId"], "me")
        raw_message = send.call_args.kwargs["body"]["raw"]
        sent_email = message_from_bytes(
            base64.urlsafe_b64decode(raw_message)
        )
        self.assertEqual(sent_email["To"], "recipient@example.com")
        self.assertEqual(sent_email["From"], "sender@example.com")
        self.assertEqual(sent_email["Reply-To"], "visitor@example.com")
        self.assertIn("Please contact me.", sent_email.get_payload())

    @patch.dict(os.environ, {"GMAIL_ADDRESS": "", "CONTACT_EMAIL": ""})
    def test_reports_missing_recipient_configuration(self):
        response = self.client.post(
            "/api/contact",
            json={
                "name": "Test User",
                "email": "visitor@example.com",
                "message": "Please contact me.",
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.get_json())

    @patch("api.create_gmail_service", side_effect=FileNotFoundError)
    def test_reports_missing_oauth_files(self, _create_service):
        response = self.client.post(
            "/api/contact",
            json={
                "name": "Test User",
                "email": "visitor@example.com",
                "message": "Please contact me.",
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()

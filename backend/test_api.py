import os
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
                "GMAIL_PASSWORD": "abcd efgh ijkl mnop",
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

    @patch("api.smtplib.SMTP")
    def test_sends_contact_email(self, smtp_class):
        response = self.client.post(
            "/api/contact",
            json={
                "name": "Test User",
                "email": "visitor@example.com",
                "message": "Please contact me.",
            },
        )

        self.assertEqual(response.status_code, 200)
        smtp = smtp_class.return_value.__enter__.return_value
        smtp.login.assert_called_once_with(
            "sender@example.com",
            "abcdefghijklmnop",
        )
        sent_email = smtp.send_message.call_args.args[0]
        self.assertEqual(sent_email["To"], "recipient@example.com")
        self.assertEqual(sent_email["Reply-To"], "visitor@example.com")

    @patch.dict(os.environ, {"GMAIL_PASSWORD": ""})
    def test_reports_missing_mail_configuration(self):
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

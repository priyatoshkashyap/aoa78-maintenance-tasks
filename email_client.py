"""
Email client module with pluggable interface for different email providers.
"""

from abc import ABC, abstractmethod
import os
import base64
import requests


class EmailClient(ABC):
    """Abstract base class for email clients."""

    @abstractmethod
    def send_email(self, to_email: str, subject: str, html_content: str, to_name: str = None) -> None:
        """Send an email with HTML content."""
        pass


class SendGridClient(EmailClient):
    """SendGrid implementation of EmailClient."""

    def __init__(self, api_key: str, from_email: str, from_name: str = None):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.url = "https://api.sendgrid.com/v3/mail/send"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def send_email(self, to_email: str, subject: str, html_content: str, to_name: str = None) -> None:
        """Send an email via SendGrid API."""
        payload = {
            "personalizations": [{"to": [{"email": to_email, "name": to_name or ""}]}],
            "from": {"email": self.from_email, "name": self.from_name or ""},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_content}]
        }

        response = requests.post(
            self.url,
            headers=self.headers,
            json=payload,
            timeout=120,
            verify=True
        )
        response.raise_for_status()


class MailjetClient(EmailClient):
    """Mailjet implementation of EmailClient."""

    def __init__(self, api_key: str, secret_key: str, from_email: str, from_name: str = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.from_email = from_email
        self.from_name = from_name or "AOA78"
        self.url = "https://api.mailjet.com/v3/send"
        credentials = f"{api_key}:{secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }

    def send_email(self, to_email: str, subject: str, html_content: str, to_name: str = None) -> None:
        """Send an email via Mailjet API."""
        payload = {
            "FromEmail": self.from_email,
            "FromName": self.from_name,
            "Recipients": [
                {"Email": to_email, "Name": to_name or "Recipient"}
            ],
            "Subject": subject,
            "Text-part": f"Please see the attached message: {subject}",
            "Html-part": html_content
        }

        response = requests.post(
            self.url,
            headers=self.headers,
            json=payload,
            timeout=120,
            verify=True
        )
        response.raise_for_status()


def get_email_client(provider: str = "sendgrid") -> EmailClient:
    """
    Factory function to get an email client instance.

    Args:
        provider: Email provider name (e.g., "sendgrid", "mailjet")

    Returns:
        EmailClient instance for the specified provider
    """
    clients = {
        "sendgrid": SendGridClient,
        "mailjet": MailjetClient,
    }

    if provider not in clients:
        raise ValueError(f"Unknown email provider: {provider}. Available: {list(clients.keys())}")

    from_email = os.getenv("EMAIL_FROM", "rwa.munirka@gmail.com")
    from_name = os.getenv("EMAIL_FROM_NAME", "RWA Munirka - AOA78")

    if provider == "mailjet":
        api_key = os.getenv("MAILJET_API_KEY")
        secret_key = os.getenv("MAILJET_SECRET_KEY")
        return clients[provider](
            api_key=api_key,
            secret_key=secret_key,
            from_email=from_email,
            from_name=from_name
        )
    else:
        api_key = os.getenv("SENDGRID_API_KEY")
        return clients[provider](api_key=api_key, from_email=from_email, from_name=from_name)

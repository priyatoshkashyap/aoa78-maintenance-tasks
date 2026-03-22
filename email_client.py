"""
Email client module with pluggable interface for different email providers.
"""

from abc import ABC, abstractmethod
import os
import requests


class EmailClient(ABC):
    """Abstract base class for email clients."""

    @abstractmethod
    def send_email(self, to_email: str, subject: str, html_content: str) -> None:
        """Send an email with HTML content."""
        pass


class SendGridClient(EmailClient):
    """SendGrid implementation of EmailClient."""

    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email
        self.url = "https://api.sendgrid.com/v3/mail/send"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def send_email(self, to_email: str, subject: str, html_content: str) -> None:
        """Send an email via SendGrid API."""
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": self.from_email},
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


def get_email_client(provider: str = "sendgrid") -> EmailClient:
    """
    Factory function to get an email client instance.

    Args:
        provider: Email provider name (e.g., "sendgrid", "smtp", "ses")

    Returns:
        EmailClient instance for the specified provider
    """
    clients = {
        "sendgrid": SendGridClient,
    }

    if provider not in clients:
        raise ValueError(f"Unknown email provider: {provider}. Available: {list(clients.keys())}")

    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("EMAIL_FROM", "rwamunirka@gmail.com")

    return clients[provider](api_key=api_key, from_email=from_email)

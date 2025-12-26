"""Mail tools package."""

from tools.mail.mail_auth import get_gmail_service
from tools.mail.get_unread_emails import get_unread_emails
from tools.mail.get_emails_by_date_range import get_emails_by_date_range
from tools.mail.get_sent_emails_by_date_range import get_sent_emails_by_date_range
from tools.mail.summarize_email import summarize_email
from tools.mail.create_draft import create_draft
from tools.mail.send_draft import send_draft
from tools.mail.list_drafts import list_drafts
from tools.mail.mark_as_read import mark_as_read

__all__ = [
    "get_gmail_service",
    "get_unread_emails",
    "get_emails_by_date_range",
    "get_sent_emails_by_date_range",
    "summarize_email",
    "create_draft",
    "send_draft",
    "list_drafts",
    "mark_as_read",
]


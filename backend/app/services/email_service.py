"""
AWS SES email integration service.

This is the ONLY file that imports boto3 for SES. All other code calls this
service for email operations. The service is injected as a FastAPI dependency,
making it easily mockable in tests.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# HTML email templates (inline constants -- no separate template files)
# ---------------------------------------------------------------------------

APPROVAL_NEEDED_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #292c2f; max-width: 600px; margin: 0 auto;">
  <div style="background-color: #292c2f; padding: 20px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Reel48+</h1>
  </div>
  <div style="padding: 30px 20px;">
    <h2 style="color: #0a6b6b; margin-top: 0;">Approval Needed</h2>
    <p>A <strong>{entity_type}</strong> requires your review and approval.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
      <tr>
        <td style="padding: 8px 0; color: #666;">Item:</td>
        <td style="padding: 8px 0; font-weight: bold;">{entity_name}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #666;">Submitted by:</td>
        <td style="padding: 8px 0;">{submitted_by_name}</td>
      </tr>
    </table>
    <div style="text-align: center; margin: 30px 0;">
      <a href="{approval_url}"
         style="background-color: #0a6b6b; color: #ffffff; padding: 12px 30px;
                text-decoration: none; border-radius: 4px; display: inline-block;">
        Review Now
      </a>
    </div>
  </div>
  <div style="background-color: #f4f4f4; padding: 15px 20px; font-size: 12px; color: #666;">
    <p style="margin: 0;">This is an automated notification from Reel48+.</p>
  </div>
</body>
</html>
"""

APPROVAL_NEEDED_TEXT = """\
Approval Needed - Reel48+

A {entity_type} requires your review and approval.

Item: {entity_name}
Submitted by: {submitted_by_name}

Review it here: {approval_url}

---
This is an automated notification from Reel48+.
"""

APPROVAL_DECISION_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #292c2f; max-width: 600px; margin: 0 auto;">
  <div style="background-color: #292c2f; padding: 20px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Reel48+</h1>
  </div>
  <div style="padding: 30px 20px;">
    <h2 style="color: {decision_color}; margin-top: 0;">
      Your {entity_type} has been {decision}
    </h2>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
      <tr>
        <td style="padding: 8px 0; color: #666;">Item:</td>
        <td style="padding: 8px 0; font-weight: bold;">{entity_name}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #666;">Decision by:</td>
        <td style="padding: 8px 0;">{decided_by_name}</td>
      </tr>
      {notes_row}
    </table>
  </div>
  <div style="background-color: #f4f4f4; padding: 15px 20px; font-size: 12px; color: #666;">
    <p style="margin: 0;">This is an automated notification from Reel48+.</p>
  </div>
</body>
</html>
"""

APPROVAL_DECISION_TEXT = """\
Your {entity_type} has been {decision} - Reel48+

Item: {entity_name}
Decision by: {decided_by_name}
{notes_line}

---
This is an automated notification from Reel48+.
"""


class EmailService:
    """Wraps AWS SES send operations via a boto3 client."""

    def __init__(self, client: Any, sender_email: str) -> None:
        self._client = client  # boto3 SES client
        self._sender_email = sender_email

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> str:
        """Send a single email via SES. Returns the SES message ID."""
        response = self._client.send_email(
            Source=self._sender_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                },
            },
        )
        message_id = response["MessageId"]
        logger.info(
            "email_sent",
            to_email=to_email,
            subject=subject,
            message_id=message_id,
        )
        return message_id

    async def send_approval_needed_notification(
        self,
        to_email: str,
        entity_type: str,
        entity_name: str,
        submitted_by_name: str,
        approval_url: str,
    ) -> str:
        """Notify an approver that something needs their review."""
        subject = f"Approval Needed: {entity_type} - {entity_name}"
        html_body = APPROVAL_NEEDED_TEMPLATE.format(
            entity_type=entity_type,
            entity_name=entity_name,
            submitted_by_name=submitted_by_name,
            approval_url=approval_url,
        )
        text_body = APPROVAL_NEEDED_TEXT.format(
            entity_type=entity_type,
            entity_name=entity_name,
            submitted_by_name=submitted_by_name,
            approval_url=approval_url,
        )
        return await self.send_email(to_email, subject, html_body, text_body)

    async def send_approval_decision_notification(
        self,
        to_email: str,
        entity_type: str,
        entity_name: str,
        decision: str,
        decided_by_name: str,
        decision_notes: str | None,
    ) -> str:
        """Notify the submitter that their submission was approved/rejected."""
        decision_color = "#0a6b6b" if decision == "approved" else "#da1e28"
        notes_row = ""
        notes_line = ""
        if decision_notes:
            notes_row = (
                f'<tr><td style="padding: 8px 0; color: #666;">Notes:</td>'
                f'<td style="padding: 8px 0;">{decision_notes}</td></tr>'
            )
            notes_line = f"Notes: {decision_notes}"

        subject = f"Your {entity_type} has been {decision}"
        html_body = APPROVAL_DECISION_TEMPLATE.format(
            entity_type=entity_type,
            entity_name=entity_name,
            decision=decision,
            decided_by_name=decided_by_name,
            decision_color=decision_color,
            notes_row=notes_row,
        )
        text_body = APPROVAL_DECISION_TEXT.format(
            entity_type=entity_type,
            entity_name=entity_name,
            decision=decision,
            decided_by_name=decided_by_name,
            notes_line=notes_line,
        )
        return await self.send_email(to_email, subject, html_body, text_body)


def get_email_service() -> EmailService:
    """FastAPI dependency that returns an EmailService with a real boto3 client."""
    import boto3  # type: ignore[import-untyped]

    client = boto3.client("ses", region_name=settings.SES_REGION)
    return EmailService(client, settings.SES_SENDER_EMAIL)

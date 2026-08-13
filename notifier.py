"""
Sends an email digest via SMTP. Works with Gmail (using an App Password),
Outlook, or any provider's SMTP details — set the environment variables
below rather than hardcoding credentials.

Required environment variables:
    SMTP_HOST   e.g. smtp.gmail.com
    SMTP_PORT   e.g. 587
    SMTP_USER   the account you're sending from
    SMTP_PASS   an app password (not your normal login password)
    ALERT_TO    where the digest should be sent
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from scraper_govuk import Grant


def build_email_body(new_eligible: list[Grant]) -> tuple[str, str]:
    subject = f"{len(new_eligible)} new eligible funding opportunit{'y' if len(new_eligible)==1 else 'ies'}"

    lines_text = []
    lines_html = ["<h2>New eligible funding opportunities</h2>"]

    for g in new_eligible:
        lines_text.append(f"{g.title}\n{g.funder}\nAmount: {g.amount_text}\nCloses: {g.closing_date_text}\n{g.url}\n")
        lines_html.append(
            f"<p><b>{g.title}</b><br>"
            f"{g.funder}<br>"
            f"Amount: {g.amount_text}<br>"
            f"Closes: {g.closing_date_text}<br>"
            f"<a href='{g.url}'>{g.url}</a></p><hr>"
        )

    body_text = "\n\n".join(lines_text)
    body_html = "\n".join(lines_html)
    return subject, body_text, body_html


def send_digest(new_eligible: list[Grant]) -> None:
    if not new_eligible:
        print("No new eligible grants — no email sent.")
        return

    required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASS", "ALERT_TO"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print(f"Email not sent — these aren't set up yet: {', '.join(missing)}.")
        print(f"({len(new_eligible)} eligible grant(s) were found — see the list above.)")
        return

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    to_addr = os.environ["ALERT_TO"]

    subject, body_text, body_html = build_email_body(new_eligible)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())

    print(f"Sent digest of {len(new_eligible)} grant(s) to {to_addr}.")

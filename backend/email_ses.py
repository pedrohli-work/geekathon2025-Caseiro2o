# backend/email_ses.py
import boto3

def _ses(aws_key, aws_secret, region):
    return boto3.client(
        "ses",
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name=region,
    )

def send_email(aws_key, aws_secret, region, sender, recipients, subject, html_body, text_body):
    if not sender:
        raise RuntimeError("SES_SENDER is not set.")
    recipients = [r.strip() for r in (recipients or []) if r and r.strip()]
    if not recipients:
        raise RuntimeError("No recipients provided.")

    ses = _ses(aws_key, aws_secret, region)
    ses.send_email(
        Source=sender,
        Destination={"ToAddresses": recipients},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": text_body, "Charset": "UTF-8"},
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        },
    )

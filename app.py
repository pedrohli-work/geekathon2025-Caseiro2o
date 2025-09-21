# app.py
import json
import streamlit as st
from datetime import datetime
from backend.s3_alerts import get_latest_alert, get_all_alerts
from backend.s3_triggers import TRIGGER_LABELS, send_trigger_txt, get_related_message
from backend.email_ses import send_email

# ================== PAGE ==================
st.set_page_config(page_title="Caseiro 2º - Alerts", page_icon="🐔", layout="centered")
st.markdown("<h1 style='text-align:center;'>🐔 Caseiro 2º</h1>", unsafe_allow_html=True)
st.caption("Trigger conditions, fetch alerts, and notify maintenance.")

# ================== SECRETS ==================
# ALERTS (alertas-caseiro)
ALERTS_KEY    = st.secrets.get("ALERTS_AWS_ACCESS_KEY_ID")
ALERTS_SECRET = st.secrets.get("ALERTS_AWS_SECRET_ACCESS_KEY")
ALERTS_REGION = st.secrets.get("ALERTS_AWS_REGION", "us-east-1")
ALERTS_BUCKET = st.secrets.get("ALERTS_BUCKET", "alertas-caseiro")
ALERTS_PREFIX = st.secrets.get("ALERTS_PREFIX", "alerts/")

# TRIGGERS (aviario-metrics)
TRIG_KEY    = st.secrets.get("TRIGGERS_AWS_ACCESS_KEY_ID")
TRIG_SECRET = st.secrets.get("TRIGGERS_AWS_SECRET_ACCESS_KEY")
TRIG_REGION = st.secrets.get("TRIGGERS_AWS_REGION", "us-east-1")
TRIG_BUCKET = st.secrets.get("TRIGGERS_BUCKET", "aviario-metrics")
TRIG_PREFIX = st.secrets.get("TRIGGERS_PREFIX", "triggers/")

# SES
SES_REGION     = st.secrets.get("SES_REGION", ALERTS_REGION)
SES_SENDER     = st.secrets.get("SES_SENDER")            # ex.: "Caseiro Alerts <you@domain.com>"
SES_RECIPIENTS = st.secrets.get("SES_RECIPIENTS", "")    # ex.: "maintenance@company.com, it@company.com"

# Presigned URL validity (minutes)
PRESIGN_MINS = 30

# ================== HELPERS ==================
def _pretty_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)

def _fmt_dt(dt: datetime) -> tuple[str, str]:
    # returns (YYYY-MM-DD, HH:MM:SS)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")

# ================== SECTION: TRIGGER ==================
st.subheader("Trigger")
st.caption("Select a trigger and send it to S3 (aviario-metrics). If a related message exists, it will be fetched and shown below.")

chosen = st.selectbox("Trigger", options=TRIGGER_LABELS, index=0)

if st.button("Send trigger", use_container_width=True):
    try:
        sent = send_trigger_txt(
            aws_key=TRIG_KEY,
            aws_secret=TRIG_SECRET,
            region=TRIG_REGION,
            bucket=TRIG_BUCKET,
            trigger_label=chosen,
            prefix=TRIG_PREFIX,
        )
        st.success(f"Trigger sent: s3://{TRIG_BUCKET}/{sent['s3_key']}")
        st.code(sent["content"], language="text")

        related = get_related_message(
            aws_key=TRIG_KEY,
            aws_secret=TRIG_SECRET,
            region=TRIG_REGION,
            bucket=TRIG_BUCKET,
            trigger_key=sent["trigger_key"],
            # will look in messages/<trigger_key>/ and info/<trigger_key>/ by default
            search_prefixes=None,
        )
        if related:
            st.info("Related message found:")
            st.caption(f"s3://{TRIG_BUCKET}/{related['s3_key']}")
            st.code(related["content"], language="text")
        else:
            st.warning("No related message found yet.")
    except Exception as e:
        st.error(str(e))

st.markdown("---")

# ================== SECTION: ALERT MESSAGES ==================
st.subheader("Alert messages")

c1, c2 = st.columns(2)
with c1:
    if st.button("Get latest message", use_container_width=True):
        try:
            latest = get_latest_alert(
                aws_key=ALERTS_KEY,
                aws_secret=ALERTS_SECRET,
                region=ALERTS_REGION,
                bucket=ALERTS_BUCKET,
                prefix=ALERTS_PREFIX,
                presign_mins=PRESIGN_MINS,
            )
            st.session_state["latest_alert"] = latest
            st.session_state["all_alerts"] = None
            st.success("Latest message loaded.")
        except Exception as e:
            st.error(str(e))

with c2:
    if st.button("Get all messages", use_container_width=True):
        try:
            all_msgs = get_all_alerts(
                aws_key=ALERTS_KEY,
                aws_secret=ALERTS_SECRET,
                region=ALERTS_REGION,
                bucket=ALERTS_BUCKET,
                prefix=ALERTS_PREFIX,
                presign_mins=PRESIGN_MINS,
                limit=None,  # set int to cap results
            )
            st.session_state["all_alerts"] = all_msgs
            st.session_state["latest_alert"] = None
            if all_msgs:
                st.success(f"Loaded {len(all_msgs)} message(s).")
            else:
                st.info("No messages found.")
        except Exception as e:
            st.error(str(e))

# Display area
if st.session_state.get("latest_alert"):
    item = st.session_state["latest_alert"]
    date_str, time_str = _fmt_dt(item["ts"])
    st.markdown(f"**#1 — {date_str} {time_str}**")
    st.write(item["data"].get("alert", "—"))
    with st.expander("Raw JSON"):
        st.code(_pretty_json(item["data"]), language="json")
    st.caption(f"Source: s3://{ALERTS_BUCKET}/{item['key']}")
    st.link_button("Open (pre-signed)", item["presigned_url"])

elif st.session_state.get("all_alerts"):
    items = st.session_state["all_alerts"]
    if items:
        # Cards with index, date/time, message
        for i, msg in enumerate(items, start=1):
            date_str, time_str = _fmt_dt(msg["ts"])
            with st.container(border=True):
                st.markdown(f"**#{i} — {date_str} {time_str}**")
                st.write(msg["data"].get("alert", "—"))
                with st.expander("Raw JSON"):
                    st.code(_pretty_json(msg["data"]), language="json")
                st.caption(f"Source: s3://{ALERTS_BUCKET}/{msg['key']}")
                st.link_button("Open (pre-signed)", msg["presigned_url"])

st.markdown("---")

# ================== SECTION: EMAIL ==================
st.subheader("Email maintenance")
st.caption("Enter recipient(s) and click send to email the selected/loaded message via Amazon SES.")

recips_str = st.text_input(
    "Recipients (comma-separated)",
    value=SES_RECIPIENTS,  # default from secrets (editable)
    placeholder="maintenance@company.com, tech@company.com"
)

# Decide which message will be emailed (latest has priority; otherwise, first of all_alerts)
selected_msg = None
if st.session_state.get("latest_alert"):
    selected_msg = st.session_state["latest_alert"]
elif st.session_state.get("all_alerts"):
    items = st.session_state["all_alerts"]
    if items:
        selected_msg = items[0]

send_disabled = selected_msg is None
if st.button("Send email", type="primary", use_container_width=True, disabled=send_disabled):
    if selected_msg is None:
        st.error("Load a message first.")
    else:
        recipients = [r.strip() for r in recips_str.split(",") if r.strip()]
        if not recipients:
            st.error("Please enter at least one recipient email.")
        else:
            data = selected_msg["data"]
            url  = selected_msg["presigned_url"]
            key  = selected_msg["key"]

            subject = f"Caseiro 2º — Alert: {data.get('alert', '')[:60]}"
            plain = (
                f"Alert message:\n{data.get('alert', '—')}\n\n"
                f"File: s3://{ALERTS_BUCKET}/{key}\n"
                f"Link: {url}\n\n"
                f"Full JSON:\n{_pretty_json(data)}\n"
            )
            html = f"""
            <h2>Caseiro 2º — Alert</h2>
            <p><b>Message:</b><br>{data.get('alert', '—')}</p>
            <p><b>File:</b> s3://{ALERTS_BUCKET}/{key}</p>
            <p><a href="{url}">Open object (pre-signed)</a></p>
            <pre style="white-space:pre-wrap">{_pretty_json(data)}</pre>
            """

            try:
                send_email(
                    aws_key=ALERTS_KEY,   # use the pair that has SES permission
                    aws_secret=ALERTS_SECRET,
                    region=SES_REGION,
                    sender=SES_SENDER,
                    recipients=recipients,
                    subject=subject,
                    html_body=html,
                    text_body=plain,
                )
                st.success("Email sent to maintenance.")
                st.toast("Email sent ✅")
            except Exception as e:
                st.error(f"Failed to send email: {e}")

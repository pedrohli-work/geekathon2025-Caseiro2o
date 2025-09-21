# backend/s3_triggers.py
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Labels exibidos no dropdown do app
TRIGGER_LABELS = [
    "trigger low air flow",
    "trigger high humidity",
    "trigger amonia",
    "trigger low temperature",
    "trigger high temperature",
    "trigger low fan velocity",
    "trigger high fan velocity",
    "trigger variable fan speed",
    "trigger variable current",
]

# Mapeamento: label -> (chave_estavel, linha_txt)
TRIGGER_MAP = {
    "trigger low air flow": ("low_air_flow", "sensor detected low airflow"),
    "trigger high humidity": ("high_humidity", "sensor detected high humidity"),
    "trigger amonia": ("ammonia", "sensor detected high ammonia"),
    "trigger low temperature": ("low_temperature", "sensor detected low temperature"),
    "trigger high temperature": ("high_temperature", "sensor detected high temperature"),
    "trigger low fan velocity": ("low_fan_velocity", "sensor detected low fan velocity"),
    "trigger high fan velocity": ("high_fan_velocity", "sensor detected high fan velocity"),
    "trigger variable fan speed": ("variable_fan_speed", "sensor detected variable fan speed"),
    "trigger variable current": ("variable_current", "sensor detected variable current"),
}

def _s3(aws_key, aws_secret, region):
    return boto3.client(
        "s3",
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name=region,
    )

def _now_iso() -> str:
    # Ex.: 2025-09-20T20:21:35.414962Z
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def send_trigger_txt(
    aws_key,
    aws_secret,
    region: str,
    bucket: str,
    trigger_label: str,
    prefix: str = "triggers/",
) -> dict:
    """
    Envia um trigger como .txt para S3 no formato:
      triggers/<trigger_key>/YYYY/MM/DD/<timestamp>.txt
    """
    if trigger_label not in TRIGGER_MAP:
        raise RuntimeError(f"Unknown trigger label: {trigger_label}")
    trigger_key, base_msg = TRIGGER_MAP[trigger_label]

    ts = _now_iso()
    dt = datetime.now(timezone.utc)

    # conteúdo do .txt
    content = (
        f"{base_msg}\n"
        f"generated_at={ts}\n"
        f"trigger_key={trigger_key}\n"
        f"source=Caseiro-UI\n"
    )

    # chave S3
    key = f"{prefix}{trigger_key}/{dt:%Y/%m/%d}/{ts}.txt"

    s3 = _s3(aws_key, aws_secret, region)
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"))
    except ClientError as e:
        raise RuntimeError(f"Failed to PUT object: {e}")

    return {"s3_key": key, "content": content, "timestamp": ts, "trigger_key": trigger_key}

def get_related_message(
    aws_key,
    aws_secret,
    region: str,
    bucket: str,
    trigger_key: str,
    search_prefixes: list[str] | None = None,
) -> dict | None:
    """
    Procura o .txt mais recente relacionado ao trigger.
    Por padrão, busca em:
      - messages/<trigger_key>/
      - info/<trigger_key>/
    Retorna { "s3_key": str, "content": str }  ou  None.
    """
    if search_prefixes is None:
        search_prefixes = [f"messages/{trigger_key}/", f"info/{trigger_key}/"]

    s3 = _s3(aws_key, aws_secret, region)

    latest_time: datetime | None = None
    latest_key: str | None = None

    for pfx in search_prefixes:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=pfx)
        for page in pages:
            for o in (page.get("Contents") or []):
                key = o.get("Key")
                if not key or not key.lower().endswith(".txt"):
                    continue
                lm = o.get("LastModified")
                if latest_time is None or (lm and lm > latest_time):
                    latest_time = lm
                    latest_key = key

    if not latest_key:
        return None

    try:
        obj = s3.get_object(Bucket=bucket, Key=latest_key)
        body = obj["Body"].read()
        return {"s3_key": latest_key, "content": body.decode("utf-8", errors="replace")}
    except ClientError:
        return None

import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

def _s3(aws_key, aws_secret, region):
    return boto3.client(
        "s3",
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name=region,
    )

def _presigned(s3, bucket, key, minutes=30):
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=minutes * 60,
    )

def _list_json(s3, bucket, prefix):
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix or "")
    objs = []
    for page in pages:
        for o in page.get("Contents", []) or []:
            if o["Key"].lower().endswith(".json"):
                objs.append(o)
    objs.sort(key=lambda x: x["LastModified"], reverse=True)
    return objs

def get_latest_alert(aws_key, aws_secret, region, bucket, prefix="alerts/", presign_mins=30):
    """Busca o alerta JSON mais recente do bucket."""
    s3 = _s3(aws_key, aws_secret, region)
    objs = _list_json(s3, bucket, prefix)
    if not objs:
        raise RuntimeError("No JSON messages found.")
    o = objs[0]
    key = o["Key"]
    raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    data = json.loads(raw.decode("utf-8"))
    return {
        "key": key,
        "data": data,
        "presigned_url": _presigned(s3, bucket, key, presign_mins),
        "ts": o["LastModified"],
    }

def get_all_alerts(aws_key, aws_secret, region, bucket, prefix="alerts/", presign_mins=30, limit=None):
    """Lista todos os alertas JSON, ordenados do mais recente pro mais antigo."""
    s3 = _s3(aws_key, aws_secret, region)
    objs = _list_json(s3, bucket, prefix)
    if limit:
        objs = objs[:limit]
    results = []
    for o in objs:
        key = o["Key"]
        try:
            raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            data = {"parse_error": str(e)}
        results.append({
            "key": key,
            "data": data,
            "presigned_url": _presigned(s3, bucket, key, presign_mins),
            "ts": o["LastModified"],
        })
    return results

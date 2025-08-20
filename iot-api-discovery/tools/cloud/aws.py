from __future__ import annotations

from typing import Any, Dict


def upload_s3(bucket: str, key: str, data: bytes, region: str | None = None) -> Dict[str, Any]:
    try:
        import boto3  # type: ignore
    except Exception as exc:
        return {"ok": False, "error": f"boto3 unavailable: {exc}"}
    try:
        session = boto3.session.Session(region_name=region)
        s3 = session.client("s3")
        s3.put_object(Bucket=bucket, Key=key, Body=data)
        return {"ok": True, "bucket": bucket, "key": key}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


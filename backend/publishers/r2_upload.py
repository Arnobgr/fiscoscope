"""Cloudflare R2 publisher — uploads data/output/*.json to the configured bucket.

See PRD §8. Credentials come from the environment (R2_ACCOUNT_ID,
R2_BUCKET_NAME, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY) — typically loaded
from `.env` by run_pipeline.py.
"""

import logging
from pathlib import Path

import boto3

from config import (
    OUTPUT_DATA_DIR,
    R2_ACCESS_KEY_ID,
    R2_ACCOUNT_ID,
    R2_BUCKET_NAME,
    R2_SECRET_ACCESS_KEY,
)

log = logging.getLogger(__name__)


def get_r2_client():
    """Build an S3 client pointed at the Cloudflare R2 endpoint."""
    missing = [
        name for name, value in [
            ("R2_ACCOUNT_ID", R2_ACCOUNT_ID),
            ("R2_BUCKET_NAME", R2_BUCKET_NAME),
            ("R2_ACCESS_KEY_ID", R2_ACCESS_KEY_ID),
            ("R2_SECRET_ACCESS_KEY", R2_SECRET_ACCESS_KEY),
        ] if not value
    ]
    if missing:
        raise RuntimeError(
            f"R2 credentials missing: {missing}. Populate .env (see PRD §7.2)."
        )
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def upload_all_outputs(prefix: str = "") -> list[str]:
    """
    Upload every JSON file in data/output/ to R2 with key = f"{prefix}{filename}".
    Returns the list of object keys uploaded.
    """
    client = get_r2_client()
    out_dir = Path(OUTPUT_DATA_DIR)
    uploaded = []
    for json_file in sorted(out_dir.glob("*.json")):
        key = f"{prefix}{json_file.name}" if prefix else json_file.name
        log.info(f"Uploading {json_file.name} → r2://{R2_BUCKET_NAME}/{key}")
        client.upload_file(
            str(json_file),
            R2_BUCKET_NAME,
            key,
            ExtraArgs={
                "ContentType": "application/json",
                "CacheControl": "public, max-age=3600",
            },
        )
        uploaded.append(key)
    log.info(f"Uploaded {len(uploaded)} files to bucket {R2_BUCKET_NAME}")
    return uploaded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for key in upload_all_outputs():
        print(f"  {key}")

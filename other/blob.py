"""Vercel Blob helper for OR/CR requirement images.

Env needed: BLOB_READ_WRITE_TOKEN   (the SDK reads it automatically)
pip install vercel
"""
import asyncio
import os
import uuid
import requests
from vercel import blob

MAX_TOTAL = 4_000_000  # stay under Vercel's ~4.5 MB request body limit

# form field name -> vehicle_requirements column
KINDS = {
    "or": "OR_path",
    "cr": "CR_path",
    "driver_license": "driver_license_path",
    "employee_id": "employee_id_path",
    "registration_form": "registration_form_path",
    "affidavit": "affidavit",
}

EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _token():
    return os.getenv("BLOB_READ_WRITE_TOKEN", "")


def _sniff(head: bytes):
    """Detect the image type from its first bytes (not the filename)."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def read_requirements(files):
    """files = request.files. Returns ({kind: (bytes, content_type)}, error)."""
    out, total = {}, 0
    for kind in KINDS:
        f = files.get(kind)
        if not f or not f.filename:
            continue
        data = f.read()
        ctype = _sniff(data[:12])
        if not ctype:
            return None, "Only JPG, PNG or WEBP images are allowed."
        total += len(data)
        out[kind] = (data, ctype)
    if not out:
        return None, "Upload at least one requirement image."
    if total > MAX_TOTAL:
        return None, "Images are too large (max about 4 MB in total)."
    return out, None


def upload(qr_id, data, ctype):
    pathname = f"requirements/{qr_id}/{uuid.uuid4().hex}.{EXT[ctype]}"

    async def _put():
        return await blob.put_blob(
            pathname,
            data,
            access="private",
            add_random_suffix=True,
            content_type=ctype,
        )

    uploaded = asyncio.run(_put())
    return uploaded.pathname, uploaded.url


def download(url):
    # private blobs need the token to be read
    r = requests.get(url, headers={"authorization": f"Bearer {_token()}"}, timeout=25)
    r.raise_for_status()
    return r.content


def save_images(sql, qr_id, images):
    """Upload to Blob and store the URLs. Returns the number of failures."""
    urls, failed = {}, 0
    for kind, (data, ctype) in images.items():
        try:
            _, url = upload(qr_id, data, ctype)
            urls[kind] = url
        except Exception as e:
            print("[BLOB] upload error:", e)
            failed += 1
    if urls and not sql.save_requirements(qr_id, urls):
        failed += len(urls)
    return failed

def remove(url):
    """Best-effort delete of a blob. Never raises."""
    try:
        async def _del():
            await blob.delete_blob(url)
        asyncio.run(_del())
    except Exception as e:
        print("[BLOB] delete error:", e)
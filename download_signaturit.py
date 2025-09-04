"""
Signaturit – Download ALL signed PDFs for a single year

What it does
------------
• Queries /v3/signatures.json with status=completed for the chosen YEAR
• Paginates with limit=100 & offset until no more results
• For every signature, fetches **signature details** (/v3/signatures/{id}.json) to reliably get signer emails
• For every document in each signature, downloads the signed PDF via:
  GET /v3/signatures/{signatureId}/documents/{documentId}/download/signed
• Saves files into ./signaturit_downloads/<YEAR>/
• If two or more documents share the same name, appends _2, _3, etc. to avoid overwriting.
• Names files using the format: <signer_emails_joined>_<original_pdf_name> (emails joined with '+')
• Writes a CSV log with signature_id, document_id, email_used, original_filename, saved_path, created_at, status, error
• Skips downloading a file if it already exists with the exact same final name (idempotent re-runs)

How to use
----------
1) Install Python 3.9+ and run:
   python -m venv .venv && .venv\\Scripts\\activate && pip install requests
2) Put your Signaturit **production** API token in the SIGNATURIT_API_TOKEN env var
   (recommended) OR paste it into the TOKEN value below.
3) Change YEAR = 2024 (or any year you want) and run: python download_signaturit.py
4) Files save under ./signaturit_downloads/<YEAR>/ and a log at ./signaturit_downloads/<YEAR>/download_log.csv

Notes
-----
• Base URL uses production: https://api.signaturit.com/v3
  If you are testing in sandbox, change BASE_URL to https://api.sandbox.signaturit.com/v3
• For the current year, the script automatically sets UNTIL to today; otherwise it uses Dec 31.
• If you have a very large year, you can also narrow by month by editing SINCE/UNTIL.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import re
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ========================= USER SETTINGS =========================
YEAR = 2024  # <-- CHANGE THIS
OUTPUT_ROOT = Path("signaturit_downloads")
TOKEN = os.getenv("SIGNATURIT_API_TOKEN") or "PASTE_YOUR_TOKEN_HERE"
PAGE_LIMIT = 100
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 1.5
BASE_URL = "https://api.signaturit.com/v3"
# ================================================================


# Return today's date in ISO format (YYYY-MM-DD)
def today_iso() -> str:
    return dt.date.today().isoformat()


# Build a date range (since, until) for the given year
def build_date_range_for_year(year: int) -> tuple[str, str]:
    since = f"{year}-01-01"
    current_year = dt.date.today().year
    until = today_iso() if year == current_year else f"{year}-12-31"
    return since, until


# Clean up filenames to remove forbidden characters
def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "document.pdf"


# Mask the token when printing to console for security
def mask_token(token: str) -> str:
    try:
        if not token:
            return "<empty>"
        if len(token) <= 12:
            return token
        return token[:6] + "..." + token[-4:]
    except Exception:
        return "<hidden>"


# Perform a GET request to the API with retry/backoff logic
def api_get(path: str, token: str, params: Optional[Dict[str, Any]] = None, stream: bool = False) -> requests.Response:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.get(url, headers=headers, params=params, stream=stream, timeout=60)
        if resp.status_code in (429, 500, 502, 503, 504):
            if attempt == MAX_RETRIES:
                return resp
            time.sleep(backoff)
            backoff *= 2
            continue
        return resp
    return resp  # type: ignore[UnboundLocalVariable]


# Fetch all signature summaries for the given year
def fetch_signatures_for_year(token: str, year: int) -> List[Dict[str, Any]]:
    since, until = build_date_range_for_year(year)
    collected: List[Dict[str, Any]] = []
    offset = 0
    while True:
        params = {"status": "completed", "since": since, "until": until, "limit": PAGE_LIMIT, "offset": offset}
        resp = api_get("/signatures.json", token, params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to list signatures: {resp.status_code} {resp.text}")
        page: List[Dict[str, Any]] = resp.json()
        if not page:
            break
        collected.extend(page)
        offset += PAGE_LIMIT
        if len(page) < PAGE_LIMIT:
            break
    return collected


# Fetch full detail for a single signature by ID
def fetch_signature_detail(token: str, signature_id: str) -> Dict[str, Any]:
    resp = api_get(f"/signatures/{signature_id}.json", token)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch signature detail {signature_id}: {resp.status_code} {resp.text}")
    return resp.json()


# Extract signer emails from signature data (summary + detail)
def extract_emails(sig_summary: Dict[str, Any], sig_detail: Optional[Dict[str, Any]] = None) -> List[str]:
    emails: List[str] = []

    def add_email(e: Optional[str]):
        if isinstance(e, str):
            e2 = e.strip()
            if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e2, flags=re.IGNORECASE):
                if e2 not in emails:
                    emails.append(e2)

    # Check structured fields first
    def harvest_from(container: Dict[str, Any]):
        for key in ("signers", "recipients", "participants"):
            items = container.get(key)
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict):
                        add_email(it.get("email"))
                        user = it.get("user")
                        if isinstance(user, dict):
                            add_email(user.get("email"))

    if isinstance(sig_detail, dict):
        harvest_from(sig_detail)
    if not emails and isinstance(sig_summary, dict):
        harvest_from(sig_summary)

    if emails:
        return emails

    # Fallback: deep search
    def walk(o: Any):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            for m in re.findall(r"[^@\s]+@[^@\s]+\.[^@\s]+", o, flags=re.IGNORECASE):
                add_email(m)

    if isinstance(sig_detail, dict):
        walk(sig_detail)
    if not emails and isinstance(sig_summary, dict):
        walk(sig_summary)

    return emails


# Ensure a folder exists (create if missing)
def ensure_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# Download the signed PDF file for a given signature/document
def download_signed_pdf(token: str, signature_id: str, document_id: str) -> bytes:
    path = f"/signatures/{signature_id}/documents/{document_id}/download/signed"
    resp = api_get(path, token, stream=True)
    if resp.status_code != 200:
        raise RuntimeError(f"Download failed ({resp.status_code}): {resp.text}")
    return resp.content


# Generate a unique filename if one already exists
def make_unique_filename(base_path: Path, filename: str) -> Path:
    stem, ext = os.path.splitext(filename)
    candidate = base_path / filename
    counter = 2
    while candidate.exists():
        candidate = base_path / f"{stem}_{counter}{ext}"
        counter += 1
    return candidate


# Main entry point: fetch signatures, download PDFs, write logs
def main() -> None:
    if (not TOKEN) or ("PASTE_YOUR_TOKEN_HERE" in TOKEN):
        raise SystemExit("No API token set. Either set SIGNATURIT_API_TOKEN or paste your token into the TOKEN variable (replace PASTE_YOUR_TOKEN_HERE).")

    since, until = build_date_range_for_year(YEAR)
    year_folder = OUTPUT_ROOT / str(YEAR)
    ensure_folder(year_folder)
    log_path = year_folder / "download_log.csv"

    print(f"Year: {YEAR} | Range: {since} → {until}")
    print(f"Using token: {mask_token(TOKEN)} | Base URL: {BASE_URL}")
    print("Fetching signatures…")
    signatures = fetch_signatures_for_year(TOKEN, YEAR)
    total_signatures = len(signatures)
    print(f"Found {total_signatures} signature request(s) in {YEAR}.")

    new_file = not log_path.exists()
    if new_file:
        with open(log_path, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["signature_id", "document_id", "email_used", "original_filename", "saved_path", "created_at", "status", "error"])

    with open(log_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        downloaded = 0
        skipped = 0
        failures = 0

        for sig in signatures:
            sig_id = sig.get("id")
            created_at = sig.get("created_at", "")
            documents = sig.get("documents", []) or []

            try:
                detail = fetch_signature_detail(TOKEN, sig_id)
            except Exception as e:
                detail = None
                print(f"! Could not fetch detail for {sig_id}: {e}")

            emails = extract_emails(sig, detail)
            email_used = "+".join(emails) if emails else ""

            if not email_used:
                # Dump debug JSON once so user can inspect structure
                debug_dir = year_folder / "_no_email_samples"
                debug_dir.mkdir(parents=True, exist_ok=True)
                debug_file = debug_dir / f"{sig_id}.json"
                if detail and not debug_file.exists():
                    debug_file.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")

            for doc in documents:
                doc_id = doc.get("id")
                file_info = doc.get("file", {}) or {}
                original_name = file_info.get("name") or f"{doc_id}.pdf"

                if email_used:
                    base_name = f"{email_used}_{original_name}"
                else:
                    base_name = original_name

                safe_name = sanitize_filename(base_name)
                if not os.path.splitext(safe_name)[1]:
                    safe_name += ".pdf"

                out_path = make_unique_filename(year_folder, safe_name)

                if out_path.exists():
                    skipped += 1
                    writer.writerow([sig_id, doc_id, email_used, original_name, str(out_path), created_at, "skipped_exists", ""])
                    continue

                try:
                    pdf_bytes = download_signed_pdf(TOKEN, sig_id, doc_id)
                    with open(out_path, "wb") as f:
                        f.write(pdf_bytes)
                    downloaded += 1
                    writer.writerow([sig_id, doc_id, email_used, original_name, str(out_path), created_at, "downloaded", ""])
                    print(f"✓ {out_path.name}")
                except Exception as e:
                    failures += 1
                    writer.writerow([sig_id, doc_id, email_used, original_name, str(out_path), created_at, "error", str(e)])
                    print(f"✗ Failed {sig_id}/{doc_id}: {e}")

    print("\nDone.")
    print(f"Downloaded: {downloaded} | Skipped (already existed): {skipped} | Failed: {failures}")
    print(f"Log saved to: {log_path}")


if __name__ == "__main__":
    main()

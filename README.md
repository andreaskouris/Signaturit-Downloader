# Signaturit Downloader

Download all **signed PDFs** from [Signaturit](https://www.signaturit.com/) for a given **year** via their REST API.  
The script paginates through signatures, fetches signer emails, names files as:


email_originalName.pdf

and logs results to a CSV file that opens cleanly in Excel (UTF-8 BOM).

---

## ✨ Features

- Download **all signed documents** for a specific year
- **Year-scoped** (no accidental full history fetch)
- Robust **pagination** (100 per page, offsets handled)
- Fetches **signer emails** from signature details
- **Email-aware filenames**: `email_originalName.pdf`
- Duplicate-safe naming: `document.pdf`, `document_2.pdf`, `document_3.pdf` …
- CSV logging with:
  - signature_id
  - document_id
  - email_used
  - original_filename
  - saved_path
  - created_at
  - status
  - error
- Retries with exponential backoff on API 429/5xx
- CSV is written with UTF-8 BOM → opens in Excel without garbling Greek letters

---

## 🛠 Requirements

- Python **3.9+**
- [Signaturit API license](https://help.signaturit.com/) and a **production API token**
- Install dependencies:
  ```bash
  pip install -r requirements.txt


📂 Repository Structure

Signaturit-Downloader/
├─ download_signaturit_year.py   # main script
├─ requirements.txt              # Python dependencies
├─ .env.example                  # template for environment variables
├─ .gitignore
├─ README.md
├─ LICENSE
└─ signaturit_downloads/         # created at runtime (ignored by git)
   └─ <YEAR>/
      ├─ download_log.csv
      ├─ _no_email_samples/      # optional debug JSONs if no email found
      └─ <downloaded PDFs>


🚀 Quick Start

1. Clone the repo
git clone https://github.com/andreaskouris/Signaturit-Downloader.git
cd Signaturit-Downloader

2. Create a virtual environment
python -m venv .venv
# Windows PowerShell
.\\.venv\\Scripts\\Activate.ps1
# macOS/Linux
source .venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. Configure your API token
Option A (recommended): environment variable
# Windows PowerShell
setx SIGNATURIT_API_TOKEN "YOUR_REAL_TOKEN"

# macOS/Linux (for current shell)
export SIGNATURIT_API_TOKEN="YOUR_REAL_TOKEN"

Option B: use a .env file
Copy .env.example → .env and fill in your token:

SIGNATURIT_API_TOKEN=YOUR_REAL_TOKEN
(Optional: install python-dotenv if you want the script to auto-load .env.)

5. Run the script
python download_signaturit.py
All PDFs + download_log.csv will be saved under signaturit_downloads/<YEAR>/

⚙️ Configuration

YEAR → which year to download

BASE_URL → defaults to production https://api.signaturit.com/v3
(use sandbox: https://api.sandbox.signaturit.com/v3)

PAGE_LIMIT → 100 (Signaturit’s max per page)

Retry logic → exponential backoff on 429/500s

📄 CSV & Excel (Greek / UTF-8)

The log is written with UTF-8 BOM so Excel opens it with Greek letters intact.
If importing manually:
Data → From Text/CSV → File Origin: Unicode (UTF-8).

🧯 Troubleshooting

401 Unauthorized → invalid/missing token. Re-set env var or .env.

Greek names look weird in Excel → open CSV with UTF-8 encoding.

Emails missing in filenames → check _no_email_samples/ JSON for how emails are structured in your account.

Too many docs (>10k) → script already splits by year. For huge years, adjust code to split by month.

🧾 .gitignore

This repo ignores:

signaturit_downloads/ (no signed docs/logs in GitHub)

.env (so tokens never get committed)

.venv/, __pycache__/, IDE configs, etc.

📜 License

MIT License – free to use and adapt.

🔮 Roadmap (nice-to-have)

CLI flags (--year 2024, --since 2021-01-01, --until 2021-06-30)

Parallel downloads with rate-limit safety

.xlsx summary report

Configurable filename templates

🤝 Contributing

PRs welcome! Please:

Keep dependencies light

Test with a narrow date range before bulk runs

Never commit real tokens or signed files


---

Do you want me to also update it so the script **auto-loads `.env`** if it exists (with `python-dotenv`)? That way, people wouldn’t need to worry about `setx` / `export`.


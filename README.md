# 📂 Signaturit Downloader

Download all **signed PDFs** from [Signaturit](https://www.signaturit.com/) for a given **year** via their REST API.  
The script paginates through signatures, fetches signer emails, names files as: 

email_originalName.pdf 


…and logs results to a CSV file that opens cleanly in Excel (UTF-8 BOM).

---

## ✨ Features

- Download all signed documents for a specific year  
- Year-scoped (no accidental full-history fetch)  
- Robust pagination (100 per page with offset)  
- Fetches signer emails from signature details  
- Email-aware filenames: `email_originalName.pdf`  
- Duplicate-safe names: `document.pdf`, `document_2.pdf`, `document_3.pdf`, …  
- CSV logging with: signature_id, document_id, email_used, original_filename, saved_path, created_at, status, error  
- Retries with exponential backoff on API 429/5xx  
- CSV opens in Excel without breaking Greek characters  

---

## 🛠 Requirements

- Python **3.9+**  
- Signaturit account with **API license** and a production API token  
- Install dependencies:
```bash
pip install -r requirements.txt
```

## 📂 Repository Structure

```perl
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
      ├─ _no_email_samples/      # debug JSONs if no email found
      └─ downloaded PDFs
```

## 🚀 Quick Start

### 1) Clone the repo
```bash
git clone https://github.com/andreaskouris/Signaturit-Downloader.git
cd Signaturit-Downloader
```

### 2) Create a virtual environment
```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Configure your API token
#### Option A – Environment variable

```powershell
# Windows PowerShell
setx SIGNATURIT_API_TOKEN "YOUR_REAL_TOKEN"
```
```bash
# macOS/Linux
export SIGNATURIT_API_TOKEN="YOUR_REAL_TOKEN"
```

#### Option B – .env file
```bash
cp .env.example .env
```
Then edit .env:
```env
SIGNATURIT_API_TOKEN=YOUR_REAL_TOKEN
```

### 5) Run the script
Edit the year inside the script:
```python
YEAR = 2024
```
Run:
```bash
python download_signaturit.py
```

All PDFs + download_log.csv will be saved under signaturit_downloads/"YEAR"/.

## ⚙️ Configuration

- YEAR → which year to download
- BASE_URL → defaults to production https://api.signaturit.com/v3 (sandbox also available)
- PAGE_LIMIT → 100 (Signaturit’s max per page)
- Retry logic → exponential backoff on 429/5xx

## 📄 CSV and Excel (Greek / UTF-8)

The log is written with UTF-8 BOM so Excel opens it with Greek letters intact.
If importing manually: Data → From Text/CSV → File Origin: Unicode (UTF-8).

## 🧯 Troubleshooting

- 401 Unauthorized → invalid or missing token
- Greek letters corrupted → import CSV as UTF-8 in Excel
- Emails missing in filenames → check _no_email_samples/*.json
- Too many docs (>10k) → split by month instead of year

## 🧾 .gitignore

This repo ignores:
  - signaturit_downloads/ (keeps docs/logs out of GitHub)
  - .env (so tokens are never committed)
  - .venv/, __pycache__, IDE configs, OS files

## 📜 License

MIT License – free to use and adapt

## 🔮 Roadmap

- CLI flags (--year, --since, --until)
- Parallel downloads with rate-limit safety
- XLSX summary report
- Configurable filename templates

## 🤝 Contributing

PRs welcome! Please:
- Keep dependencies light
- Test with a narrow date range before bulk runs
- Never commit real tokens or signed files

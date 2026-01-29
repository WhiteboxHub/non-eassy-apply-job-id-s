# LinkedIn Job Extractor & Marketing Bot

A powerful automated tool to extract LinkedIn job postings and save them directly to a MySQL database and CSV files. Targeted for high-speed job data collection with anti-detection features.

## 🌟 Key Features

*   **Anti-Detection**: Uses `undetected-chromedriver` and `selenium-stealth` to mimic real browser behavior.
*   **Persistent Profiles**: Saves and reuses your Chrome session (no need to log in every time).
*   **Aggressive Scrolling**: Smart scrolling logic that ensures every job listing on the page is loaded.
*   **Dual Storage**: Automatically saves data to:
    1.  **MySQL Database**: Direct insertion into your `position` table.
    2.  **CSV Files**: Per-candidate job lists for easy viewing in Excel.
*   **Multi-Keyword Search**: Automatically iterates through multiple job titles and locations.

---

## 🛠️ Setup Instructions

### 1. Prerequisites
- Python 3.10+
- Google Chrome installed on your system.
- A running MySQL database.

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Configuration (.env)
Create a `.env` file in the root directory (or update the existing one):
```ini
# LinkedIn Credentials (Optional if using persistent profile)
LINKEDIN_USERNAME=your_email@gmail.com
LINKEDIN_PASSWORD=your_password

# MySQL Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=your_database_name
DB_PORT=3306
```

### 4. Candidate Configuration (candidate_marketing.yaml)
Manage your search terms and locations in `candidate_marketing.yaml`:
```yaml
candidates:
  - candidate_id: "candidate_001"
    name: "John Doe"
    linkedin_username: "your_email@gmail.com"
    linkedin_password: "your_password"
    keywords:
      - "AI/ML Engineer"
      - "Python Developer"
    locations:
      - "Remote"
      - "560100" # Zipcodes supported
```

---

## ▶️ How to Run

1. **Close all Chrome windows** (The bot needs to control the profile).
2. Start the extraction:
   ```bash
   python daily_extractor.py
   ```
3. The bot will open Chrome, navigate to LinkedIn, and start extracting jobs. If you aren't logged in, it will pause and let you log in manually once.

---

## 📂 Data Output

- **CSV**: Found in the root directory (e.g., `yourname_extracted_jobs.csv`).
- **MySQL**: Data is inserted into the `position` table with fields parsed for `city`, `state`, and `zip`.
- **Profiles**: Browser data is stored in `data/profiles/` to keep you logged in.

---

## 🔧 Troubleshooting

- **Version Mismatch**: If you see a Chrome version error, the bot automatically attempts to fix it. If it fails, update your Google Chrome.
- **MySQL Access Denied**: Double-check your `.env` credentials and ensure the `position` table exists.
- **Bot Stuck**: Ensure no other Chrome process is using your profile folder.

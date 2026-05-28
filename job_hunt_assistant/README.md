# AI Job Hunt Assistant

Private Streamlit app for finding jobs, scoring them against a resume, generating tailored application assets, and tracking submitted applications.

## What Is Production-Ready Now

- Password-gated Streamlit UI with per-user access configured through secrets.
- Hashed passwords using PBKDF2-SHA256. Do not store plaintext passwords.
- API keys and user credentials kept out of git through `.env` and Streamlit secrets.
- Generated resumes, cover letters, logs, and local virtual environments ignored by git.
- Cleaner first screen with shortlist/package metrics and simpler sidebar flow.

## Local Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `utils/.env` locally:

```env
GROQ_API_KEY=your_key_here
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
```

Generate password hashes:

```powershell
python scripts\hash_password.py
```

Create `.streamlit/secrets.toml` from `.streamlit/secrets.example.toml` and paste the generated hash:

```toml
[auth.users.owner]
username = "owner@example.com"
display_name = "Owner"
password_hash = "pbkdf2_sha256$..."
```

Run the app:

```powershell
streamlit run streamlit_app.py
```

## Deployment Recommendation

For the current Streamlit version of this product, use Streamlit Community Cloud first.

Streamlit Community Cloud is the fastest free route because it is built for Streamlit, connects directly to GitHub repositories, supports app secrets, and supports private app sharing by email. This is best for demos, private beta users, and early paid pilots.

Azure App Service is better when you need custom domains, stronger control, monitoring, and a more standard production environment. Azure has a free App Service SKU for Python apps, but Streamlit usually needs more setup than Streamlit Community Cloud. Azure Static Web Apps is not the right fit for this app because Streamlit is a running Python web server, not a static front end.

## Streamlit Community Cloud Steps

1. Push this folder to GitHub.
2. In Streamlit Community Cloud, create a new app from the repo.
3. Set the main file path to `streamlit_app.py`.
4. Add secrets in the app settings:

```toml
GROQ_API_KEY = "your_key_here"
LLM_PROVIDER = "groq"
LLM_MODEL = "llama-3.3-70b-versatile"

[auth.users.owner]
username = "owner@example.com"
display_name = "Owner"
password_hash = "pbkdf2_sha256$..."
```

5. Keep the app private and invite only approved users by email.

## Azure App Service Notes

Use Azure App Service for Linux with a startup command similar to:

```bash
python -m streamlit run streamlit_app.py --server.port 8000 --server.address 0.0.0.0
```

Set API keys and `JOB_ASSISTANT_USERS` as App Service application settings:

```env
JOB_ASSISTANT_USERS=owner@example.com:pbkdf2_sha256$...
```

## Features Worth Adding Before Selling

- User workspaces: separate each user resume, generated files, and application log.
- Resume profile vault: allow multiple base resumes for different target roles.
- Saved searches and alerts: store preferred keywords, locations, and companies.
- Pipeline dashboard: Kanban view for found, shortlisted, generated, submitted, interview, rejected.
- One-click export: ZIP package with tailored resume, cover letter, outreach message, and application notes.
- Payment and license control: Stripe checkout plus account status checks.
- Admin panel: invite users, disable access, view usage, and manage plan limits.
- Better data storage: move from local CSV/files to Postgres, Supabase, or Azure SQL.
- Background jobs: run scraping and generation asynchronously so the UI does not freeze.
- Legal/safety copy: make clear that the tool assists applications and does not submit without user approval.

## Important Production Caveat

The current app is suitable for a private beta or early client demo. Before selling broadly to individuals, add database-backed user isolation so one customer cannot see another customer's generated resumes, cover letters, or application history.

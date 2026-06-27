# 🌐 Internet Deployment Guide: Job Application Generator Web App

This guide explains how to easily deploy your Streamlit Web Application (`app_web.py`) to the public internet so that anyone can access and use it!

---

## 🚀 Option 1: Streamlit Community Cloud (Easiest & Free)

Streamlit Community Cloud allows you to deploy directly from your GitHub repository in just a few clicks.

### Prerequisites Built-In
Your repository already includes everything needed for Streamlit Community Cloud:
- `requirements.txt`: Contains all necessary Python packages (`streamlit`, `PySide6`, `google-generativeai`, `pypdf`, etc.).
- `packages.txt`: Contains the Debian system dependencies needed to compile LaTeX and compress PDFs (`texlive-latex-base`, `texlive-fonts-recommended`, `ghostscript`, etc.).

### Deployment Steps
1. **Push Changes:** Ensure your repository is fully pushed to GitHub.
2. **Log In:** Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
3. **Deploy App:** Click **"New app"** -> **"Use existing repo"**.
4. **Configure Settings:**
   - **Repository:** `MicroscopeMaestro/Jobs`
   - **Branch:** `main`
   - **Main file path:** `app_web.py`
5. **Advanced Settings (Optional):** If you want to provide a default API key, click "Advanced settings" and add `GEMINI_API_KEY=your_api_key` in the Secrets box. (Alternatively, users can input their own API keys securely via the sidebar in the web app).
6. **Launch:** Click **"Deploy!"** Streamlit will automatically install the system packages and launch your public web application!

---

## 🐳 Option 2: Docker Deployment (Cloud Run, Railway, Render, Hugging Face)

For dedicated container hosting or cloud providers like Google Cloud Run, Railway, Render, or Hugging Face Spaces (Docker mode), a professional `Dockerfile` is included.

### How It Works
The provided `Dockerfile`:
1. Uses a lightweight Python 3.11 base image.
2. Automatically installs TeX Live and Ghostscript via `apt-get`.
3. Installs all Python dependencies.
4. Exposes port `8501` and runs `app_web.py` in headless mode.

### Sample Deployment Commands (Local / VPS)
To build and run the Docker container locally or on a private VPS:
```bash
# Build the Docker image
docker build -t job-generator-web .

# Run the container on port 8501
docker run -p 8501:8501 -e GEMINI_API_KEY="your_api_key" job-generator-web
```

---

## 🔒 Security & Multi-User Notes
- **Secure API Key Input:** Users who visit your public web app can securely enter their own Gemini, Kimi, or Anthropic API Keys in the left sidebar.
- **Session State:** Streamlit maintains separate UI session states for each concurrent user visiting the web app.

# ai-bi-insight-generator
**📌 AI-Powered Tableau Dashboard Insights & Email Automation**
🚀 Overview
This project automates the process of fetching dashboard images from Tableau Public, generating AI-powered insights, and sending them via beautifully formatted emails — all for free.

The workflow runs on a schedule without depending on your laptop, ensuring hands-free daily/weekly reports.

✨ Features
📊 Fetch Tableau Public dashboard snapshots automatically
🤖 Generate insights from images using AI
💌 Send insights via email with images and PDFs attached
🕒 Automated scheduling using GitHub Actions (no PC needed)
💸 100% Free — uses free-tier AI & scheduling tools

🛠 Tools & Technologies
Python 🐍 – automation & data handling
Groq API – AI text generation from dashboard images
Pandas – data processing
Tableau Public – dashboard hosting
SMTP (Gmail) – sending email
GitHub Actions – free cloud scheduling

📷 Demo Output
<img width="234" height="370" alt="image" src="https://github.com/user-attachments/assets/d57202a5-39cc-4217-964b-5762f6dfd398" />


⚡ How It Works
Download the Tableau dashboard image
Send image to AI for insight extraction
Format insights into a polished HTML email
Send to recipients with dashboard attachments
Repeat automatically on your chosen schedule

📂 Project Structure
bash
Copy
Edit
📁 project/
 ├── config.py           # API keys & email settings
 ├── main.py             # Main automation script
 ├── requirements.txt    # Dependencies
 ├── .env                # Environment variables
 ├── .github/workflows   # GitHub Actions automation

💡 Why This Project?
This project showcases how AI can transform static dashboards into actionable insights automatically, making it ideal for:

BI Analysts

Marketing Teams

Freelancers delivering client reports

Anyone who wants to automate reporting without extra cost



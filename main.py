import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 1. Read secrets
tableau_url = os.getenv("TABLEAU_PUBLIC_URL")
groq_api_key = os.getenv("GROQ_API_KEY")
email_user = os.getenv("EMAIL_USER")
email_pass = os.getenv("EMAIL_PASS")
email_to = os.getenv("EMAIL_TO")
smtp_host = os.getenv("SMTP_HOST")
smtp_port = int(os.getenv("SMTP_PORT", "587"))

# 2. TODO: Replace with actual Tableau Public scraping / API logic
# For now, use dummy data
data = {
    "Revenue": 120000,
    "Expenses": 80000,
    "Profit": 40000
}

# 3. Generate insights (placeholder)
insights = f"""
📊 **Daily BI Insights**

- Revenue: ${data['Revenue']:,}
- Expenses: ${data['Expenses']:,}
- Profit: ${data['Profit']:,}

URL: {tableau_url}
"""

# 4. Send email
msg = MIMEMultipart()
msg["From"] = email_user
msg["To"] = email_to
msg["Subject"] = "Daily BI Insights"

msg.attach(MIMEText(insights, "plain"))

with smtplib.SMTP(smtp_host, smtp_port) as server:
    server.starttls()
    server.login(email_user, email_pass)
    server.send_message(msg)

print("Email sent successfully!")

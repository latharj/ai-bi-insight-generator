import os, ssl, smtplib, requests
from pathlib import Path
from email.message import EmailMessage
from email.utils import formatdate
from html import escape

from PIL import Image
import numpy as np
import easyocr
from groq import Groq

# --------- Paths & Env ---------
ROOT = Path(__file__).parent
OUT  = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

PUBLIC_URL   = os.getenv("TABLEAU_PUBLIC_URL")   # from GitHub Secrets
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

EMAIL_USER   = os.getenv("EMAIL_USER")
EMAIL_PASS   = os.getenv("EMAIL_PASS")
EMAIL_TO     = os.getenv("EMAIL_TO", EMAIL_USER)
SMTP_HOST    = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT    = int(os.getenv("SMTP_PORT", "587"))

PNG_PATH = OUT / "dashboard.png"
PDF_PATH = OUT / "dashboard.pdf"
SUMMARY_TXT = OUT / "ai_summary_from_png.txt"


# --------- Helpers ---------
def _u(base: str, suffix: str) -> str:
    """Join a Tableau public views URL with an export suffix."""
    return base.split("?")[0] + suffix

def fetch_png_pdf(view_url: str):
    """Download PNG + PDF from Tableau Public export endpoints."""
    # Try two PNG variants (different deployments behave differently)
    for u in (
        _u(view_url, ".png?:showVizHome=no&:toolbar=no"),
        _u(view_url, "?:showVizHome=no&:format=png&:toolbar=no"),
    ):
        r = requests.get(u, timeout=120)
        if r.ok and r.content:
            PNG_PATH.write_bytes(r.content)
            break
    else:
        raise RuntimeError("PNG export failed from Tableau Public.")

    # PDF
    r = requests.get(_u(view_url, ".pdf?:showVizHome=no&:toolbar=no"), timeout=180)
    r.raise_for_status()
    PDF_PATH.write_bytes(r.content)

def do_ocr(png_path: Path) -> str:
    """OCR the PNG using EasyOCR and return joined text."""
    img = Image.open(png_path).convert("RGB")
    # upscale a bit to help OCR
    w, h = img.size
    img = img.resize((int(w*1.4), int(h*1.4)))
    arr = np.array(img)

    reader = easyocr.Reader(['en'], gpu=False)
    lines = reader.readtext(arr, detail=0, paragraph=True)  # list[str]
    return "\n".join(l.strip() for l in lines if l and l.strip())

def groq_insights(ocr_text: str, api_key: str) -> str:
    """Use Groq (Llama 3.1) to turn OCR text into crisp insights + actions."""
    client = Groq(api_key=api_key)
    prompt = f"""You are a senior BI analyst. The text below was OCR'd from a Tableau dashboard image.
Write 4 concise insights and 1 practical action per insight. Use concrete numbers if present.
Format as:

Insight 1: ...
Action: ...
(blank line)
Insight 2: ...
Action: ...
...

OCR TEXT:
{ocr_text}
"""
    r = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role":"user","content":prompt}],
        temperature=0.2,
    )
    return r.choices[0].message.content.strip()

def summary_to_cards(summary_text: str) -> list[dict]:
    """Light parser that turns 'Insight X / Action:' blocks into cards."""
    blocks = [b.strip(" -*\n") for b in summary_text.split("\n\n") if b.strip()]
    cards, i = [], 1
    cur = {"title": f"Insight {i}", "finding": "", "action": ""}
    for b in blocks:
        low = b.lower()
        if low.startswith("insight"):
            if cur["finding"] or cur["action"]:
                cards.append(cur); i += 1
                cur = {"title": f"Insight {i}", "finding": "", "action": ""}
            cur["title"] = b.split(":",1)[0].strip() if ":" in b else f"Insight {i}"
            if ":" in b: cur["finding"] = b.split(":",1)[1].strip()
        elif low.startswith("action"):
            cur["action"] = b.split(":",1)[1].strip() if ":" in b else b
        else:
            cur["finding"] = (cur["finding"]+" "+b).strip() if cur["finding"] else b
    if cur["finding"] or cur["action"]:
        cards.append(cur)
    return cards

def render_email_html(dashboard_url: str, insights: list[dict], cid: str = "dash") -> str:
    def card(it, i):
        return f"""
          <tr>
            <td style="padding:16px;border:1px solid #e9edf3;border-radius:12px;background:#ffffff;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
                <tr><td style="font:600 16px/1.3 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0f172a;padding-bottom:6px;">
                  🔹 {escape(it.get('title', f'Insight {i}'))}
                </td></tr>
                <tr><td style="font:400 14px/1.6 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#334155;padding-bottom:10px;">
                  <b>Finding:</b> {escape(it.get('finding',''))}
                </td></tr>
                <tr><td style="font:400 14px/1.6 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#334155;">
                  <b>Action:</b> {escape(it.get('action',''))}
                </td></tr>
              </table>
            </td>
          </tr>
          <tr><td style="height:14px"></td></tr>
        """
    cards_html = "".join(card(it, i+1) for i, it in enumerate(insights))
    button_html = f"""
      <table role="presentation" cellspacing="0" cellpadding="0">
        <tr><td align="center" bgcolor="#2563eb" style="border-radius:10px;">
          <a href="{escape(dashboard_url)}" target="_blank"
             style="display:inline-block;padding:12px 18px;font:600 14px/1 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#ffffff;text-decoration:none;border-radius:10px;">
            View Dashboard
          </a>
        </td></tr>
      </table>
    """
    return f"""<!doctype html><html><body style="margin:0;padding:0;background:#f6f8fb;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6f8fb;">
    <tr><td align="center" style="padding:28px 16px;">
      <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border-radius:16px;border:1px solid #e9edf3;">
        <tr><td style="padding:22px 24px 8px 24px;">
          <table role="presentation" width="100%"><tr>
            <td style="font:700 20px/1.3 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0f172a;">📊 Dashboard OCR — AI Insights</td>
            <td align="right" style="font:400 12px/1.4 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#64748b;">Automated report</td>
          </tr></table>
        </td></tr>
        <tr><td style="padding:12px 24px 0 24px;">{button_html}</td></tr>
        <tr><td style="padding:14px 24px 0 24px;"><img src="cid:dash" alt="Dashboard snapshot" width="592" style="width:100%;max-width:592px;border-radius:12px;border:1px solid #e9edf3;display:block;"></td></tr>
        <tr><td style="height:18px"></td></tr>
        <tr><td style="padding:0 24px 8px 24px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            <tr><td style="font:700 16px/1.4 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0f172a;">Key Insights & Actions</td></tr>
            <tr><td style="height:10px"></td></tr>
            {cards_html}
          </table>
        </td></tr>
        <tr><td style="padding:8px 24px 22px 24px;">
          <table role="presentation" width="100%"><tr>
            <td style="font:400 12px/1.6 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#64748b;">
              Sent automatically • Attachments: PDF and summary<br/>
              If the snapshot looks fuzzy, open the dashboard for the interactive version.
            </td>
          </tr></table>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

def send_email(subject: str, text_body: str, html_body: str, inline_png: Path, attachments: list[Path]):
    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if inline_png.exists():
        msg.get_payload()[1].add_related(inline_png.read_bytes(), maintype="image", subtype="png", cid="dash")

    for p in attachments:
        if p and p.exists():
            ext = p.suffix.lower()
            if ext == ".pdf":
                msg.add_attachment(p.read_bytes(), maintype="application", subtype="pdf", filename=p.name)
            elif ext in (".txt", ".md"):
                msg.add_attachment(p.read_bytes(), maintype="text", subtype="plain", filename=p.name)
            elif ext == ".png":
                msg.add_attachment(p.read_bytes(), maintype="image", subtype="png", filename=p.name)
            else:
                msg.add_attachment(p.read_bytes(), filename=p.name)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls(context=ctx)
        s.login(EMAIL_USER, EMAIL_PASS)
        s.send_message(msg)

# --------- Main ---------
def main():
    assert PUBLIC_URL, "TABLEAU_PUBLIC_URL is required"
    assert GROQ_API_KEY, "GROQ_API_KEY is required"
    assert EMAIL_USER and EMAIL_PASS, "Email credentials missing"

    # 1) Fetch PNG + PDF from Tableau Public
    fetch_png_pdf(PUBLIC_URL)

    # 2) OCR the PNG
    ocr_text = do_ocr(PNG_PATH) or "(no text extracted)"

    # 3) Ask Groq for insights
    summary = groq_insights(ocr_text, GROQ_API_KEY)
    SUMMARY_TXT.write_text(summary, encoding="utf-8")

    # 4) Email (HTML + inline PNG + PDF + summary)
    cards = summary_to_cards(summary)
    html_body = render_email_html(PUBLIC_URL, cards, cid="dash")
    plain_body = f"Dashboard: {PUBLIC_URL}\n\n{summary}\n\n(Attachments: PDF + OCR summary)"

    send_email(
        subject="Dashboard — AI Insights",
        text_body=plain_body,
        html_body=html_body,
        inline_png=PNG_PATH,
        attachments=[PDF_PATH, SUMMARY_TXT],
    )
    print("✅ Email sent")

if __name__ == "__main__":
    main()

import imaplib
import email
import re
import json
from google import genai
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import email.utils
from models import EventUpdateLog

from models import db, Event, User


MAIL_USER = "jamirahmadmulani8@gmail.com"
MAIL_PASS = "nqdauwwjnnmzxygu"
GEMINI_API_KEY = "" 

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

def clean_email(msg):
    body = ""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    body += part.get_payload(decode=True).decode(errors="ignore")
                elif content_type == "text/html":
                    html = part.get_payload(decode=True).decode(errors="ignore")
                    body += BeautifulSoup(html, "html.parser").get_text()
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")
    except:
        pass
    return body.strip()


def extract_data_with_gemini(subject, body):
    prompt = f"""
    Analyze this email thread. Extract event details.
    
    CRITICAL RULES:
    1. If the user mentions an ID like (Event ID: 16), extract it as 'event_id'.
    2. Date MUST be in 'YYYY-MM-DD HH:MM:SS' format. 
    3. If the user DID NOT provide a new date, set 'date' to null. 
    4. Do not use formats like 'Thu, Apr 23'.

    Return ONLY JSON:
    {{
      "event_id": "integer or null",
      "name": "string or null",
      "location": "string or null",
      "date": "string or null",
      "description": "string or null"
    }}

    Subject: {subject}
    Body: {body}
    """
    
    try:
        response = model.generate_content(prompt)
        json_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_text)
    except Exception as e:
        print(f" Gemini Error: {e}")
        return None


def read_email_replies(app, user_id):
    updated_events = []  
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(" User not found")
            return []

        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(MAIL_USER, MAIL_PASS)
            mail.select("INBOX")
        except Exception as e:
            print(" Login failed:", e)
            return []

        today = datetime.now().strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{today}" UNSEEN)')

        if not messages or not messages[0]:
            mail.logout()
            return []

        now = datetime.now(timezone.utc)

        for num in messages[0].split():
            try:
                _, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                # 30 Mins Check
                date_str = msg.get("Date")
                if date_str:
                    email_dt = email.utils.parsedate_to_datetime(date_str)
                    if now - email_dt > timedelta(minutes=30):
                        continue 

                subject = msg.get("subject", "")
                body = clean_email(msg)
                data = extract_data_with_gemini(subject, body)
                
                if not data:
                    continue

                # Target Specific Record
                event = None
                if data.get("event_id"):
                    event = Event.query.get(data["event_id"])
                
                if not event:
                    event = Event.query.filter_by(created_by=user.id)\
                                       .filter((Event.location == None) | (Event.description == None))\
                                       .order_by(Event.id.desc()).first()

                if not event:
                    continue

               
                changes = []

                
                if data.get("name"):
                    event.name = data["name"]
                if data.get("location") and data["location"] != "null":
                    event.location = data["location"]
                    changes.append("Location") # Added tracking
                if data.get("description") and data["description"] != "null":
                    event.description = data["description"]
                    changes.append("Description") # Added tracking

                # Date Format Fix
                if data.get("date"):
                    try:
                        valid_date = datetime.strptime(data["date"], '%Y-%m-%d %H:%M:%S')
                        event.date = valid_date
                        changes.append("Date") # Added tracking
                    except (ValueError, TypeError):
                        print(f" Invalid date format ignored: {data['date']}")

                db.session.commit()
                print(f"DB UPDATED FOR EVENT ID {event.id}")
                log = EventUpdateLog(
                    event_id=event.id,
                    name=event.name,
                    location=event.location,
                    description=event.description,
                    date=event.date,
                    fields_changed=", ".join(changes) if changes else "Details Updated"
                    
                )
                db.session.add(log)
                db.session.commit()

                # 2. Yahan list mein data add kiya (Sath mein 'fields_changed' bhi bhej diya)
                updated_events.append({
                    'id': event.id,
                    'name': event.name,
                    'location': event.location,
                    'date': event.date.strftime('%Y-%m-%d %H:%M:%S') if isinstance(event.date, datetime) else event.date,
                    'description': event.description,
                    'fields_changed': ", ".join(changes) if changes else "Details Updated" # Ye naya field hai
                })

                mail.store(num, "+FLAGS", "\\Seen")

            except Exception as e:
                print(f" ERROR: {e}")
                db.session.rollback()

        mail.logout()
    
    # 3. Last mein list return kar di
    return updated_events
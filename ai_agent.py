import os
import re
from google import genai
from langgraph.graph import StateGraph
from models import Event
from dotenv import load_dotenv

load_dotenv()


#  GEMINI CLIENT

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

#  WORKING MODEL
MODEL = "gemini-flash-latest"



#  DATABASE SEARCH NODE

def fetch_data(state):
    query = state.get("query", "").lower()

    try:
        ids = re.findall(r'\d+', query)

        #  ID SEARCH
        if "id" in query and ids:
            event = Event.query.get(int(ids[0]))
            if event:
                return {
                    "query": query,
                    "data": f"Event: {event.name}, Date: {event.date}, Location: {event.location}"
                }

        #  LOCATION SEARCH
        events = Event.query.filter(Event.location.ilike(f"%{query}%")).all()
        if events:
            return {
                "query": query,
                "data": ", ".join([f"{e.name} on {e.date} at {e.location}" for e in events])
            }

        #  NAME SEARCH
        events = Event.query.filter(Event.name.ilike(f"%{query}%")).all()
        if events:
            return {
                "query": query,
                "data": ", ".join([f"{e.name} on {e.date} at {e.location}" for e in events])
            }

        return {"query": query, "data": None}

    except Exception:
        return {"query": query, "data": None}


def generate_ai_response(state):

    query = state.get("query", "")
    data = state.get("data")

    #  STRONG PROMPT (4–5 LINE EXPLANATION)
    if data:
        prompt = f"""
You are an AI Event Assistant.

User Query: {query}

Database Result:
{data}

Instructions:
- Explain the result clearly
- Give 4 to 5 lines response
- Make it human friendly
- Add small guidance if needed
"""
    else:
        prompt = f"""
You are an AI Event Assistant.

User Query: {query}

No matching event found in database.

Instructions:
- Give 4 to 5 lines explanation
- Suggest how user can search (id, name, location)
- Be helpful and friendly
"""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        return {"response": response.text}

    except Exception as e:
        return {"response": f"AI Error: {str(e)}"}


#  LANGGRAPH FLOW

builder = StateGraph(dict)

builder.add_node("db_fetch", fetch_data)
builder.add_node("ai_response", generate_ai_response)

builder.set_entry_point("db_fetch")
builder.add_edge("db_fetch", "ai_response")

graph = builder.compile()






def extract_fields_from_email(body):

    prompt = f"""
Extract event details from the email.

Email:
{body}

Return ONLY JSON format:

{{
  "event_id": "",
  "name": "",
  "date": "",
  "location": "",
  "description": ""
}}
"""

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt
    )

    return response.text
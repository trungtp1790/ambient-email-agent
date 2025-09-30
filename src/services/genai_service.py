from google import genai
import os
import json
import logging
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"  # Updated to latest model

_client = None
def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_GENERATIVE_AI_API_KEY environment variable is required")
        _client = genai.Client(api_key=api_key)
    return _client

def classify_email(subject: str, body: str, sender: str = "") -> str:
    """Classify email into needs_reply, schedule, fyi, or spam"""
    try:
        prompt = f"""
You are an email triage expert. Analyze the email and classify it strictly into one of these categories:

- needs_reply: Requires a response or action from the recipient
- schedule: Meeting requests, calendar invitations, or scheduling-related
- fyi: Informational emails that don't require immediate action
- spam: Unsolicited, promotional, or suspicious emails

Email details:
Subject: {subject}
From: {sender}
Body: {body[:500]}...

Return ONLY a JSON object with the email_type field:
{{
  "email_type": "needs_reply|schedule|fyi|spam"
}}
""".strip()
        
        resp = get_client().models.generate_content(model=MODEL, contents=prompt)
        response_text = (resp.text or "").strip()
        
        # Parse JSON response - handle markdown code blocks
        try:
            # Remove markdown code block markers if present
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove ```
            cleaned_response = cleaned_response.strip()
            
            result = json.loads(cleaned_response)
            label = result.get("email_type", "").lower()
            
            # Validate response
            valid_labels = {"needs_reply", "schedule", "fyi", "spam"}
            if label in valid_labels:
                logger.info("Email classified as: %s", label)
                return label
            else:
                logger.warning("Invalid classification '%s', defaulting to 'fyi'", label)
                return "fyi"
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse JSON response: %s, raw response: %s", e, response_text)
            # Fallback: try to extract category from text if JSON parsing fails
            response_lower = response_text.lower()
            if "needs_reply" in response_lower:
                return "needs_reply"
            elif "schedule" in response_lower:
                return "schedule"
            elif "spam" in response_lower:
                return "spam"
            else:
                return "fyi"
            
    except (ValueError, RuntimeError, ConnectionError) as e:
        logger.error("Error classifying email: %s", e)
        # Fallback heuristic when model quota/exceptions happen
        text = f"{subject}\n{body}".lower()
        # Very simple rules to still surface actionable emails
        needs_reply_keywords = [
            "please reply", "vui lòng", "trả lời", "confirm", "xác nhận",
            "yes/no", "phản hồi", "deadline", "by eod", "can you", "could you",
            "có thể", "được không", "feedback", "ý kiến", "review", "kiểm tra",
            "?"
        ]
        schedule_keywords = [
            "meet", "meeting", "schedule", "hẹn", "calendar", "call",
            "họp", "gặp", "lịch", "cuộc họp", "hẹn gặp", "lịch trình"
        ]
        spam_keywords = [
            "unsubscribe", "viagra", "crypto", "lottery", "win money", "win $", 
            "congratulations", "prize", "claim", "click here", "free money",
            "urgent", "act now", "limited time", "guaranteed", "no risk",
            "chúc mừng", "trúng thưởng", "nhận thưởng", "khuyến mãi", "giảm giá",
            "đầu tư", "kiếm tiền", "không rủi ro", "cơ hội duy nhất"
        ]

        if any(k in text for k in spam_keywords):
            return "spam"
        if any(k in text for k in schedule_keywords):
            return "schedule"
        if any(k in text for k in needs_reply_keywords):
            return "needs_reply"
        return "fyi"

def draft_reply(subject: str, body: str, tone: str, pref_hours: str, sender: str = "", vip_contacts: List[str] = None) -> str:
    """Generate a contextual reply draft using Gemini"""
    try:
        vip_context = ""
        if vip_contacts and sender in vip_contacts:
            vip_context = " (This is a VIP contact - be extra professional and responsive)"
        
        prompt = f"""
You are a professional email assistant. Write a concise, contextual reply to this email.

Instructions:
- Tone: {tone}
- If scheduling is mentioned, suggest times within: {pref_hours}
- Be professional and helpful{vip_context}
- Keep the reply concise but complete
- Match the formality level of the original email

Original email:
Subject: {subject}
From: {sender}
Body: {body[:800]}...

Write your reply (without <reply></reply> tags):
""".strip()
        
        resp = get_client().models.generate_content(model=MODEL, contents=prompt)
        reply = resp.text or ""
        
        if reply:
            logger.info("Generated reply draft for %s", sender)
            return reply.strip()
        else:
            logger.warning("Empty reply generated")
            return "Thank you for your email. I will review it and get back to you soon."
            
    except (ValueError, RuntimeError, ConnectionError) as e:
        logger.error("Error generating reply: %s", e)
        return "Thank you for your email. I will review it and get back to you soon."
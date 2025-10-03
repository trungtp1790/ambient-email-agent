"""
GenAI Service - Google Gemini AI Integration
===========================================

Service này cung cấp các chức năng AI:
- Email classification (needs_reply, schedule, fyi, spam)
- Draft reply generation với context awareness
- VIP contact recognition
- Fallback heuristics khi AI fails

Architecture:
- Sử dụng Google Gemini 2.5 Flash model
- Prompt engineering cho classification và generation
- Error handling với fallback rules
- Caching client instance
"""

from google import genai
import os
import json
import logging
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini model configuration
MODEL = "gemini-2.5-flash"  # Latest model với tốc độ cao

# Client caching
_client = None

def get_client():
    """
    Lấy hoặc tạo Gemini AI client instance
    
    Sử dụng singleton pattern để cache client và tránh tạo lại
    
    Returns:
        genai.Client instance
        
    Raises:
        ValueError: Nếu không có API key
    """
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_GENERATIVE_AI_API_KEY environment variable is required")
        _client = genai.Client(api_key=api_key)
    return _client

def classify_email(subject: str, body: str, sender: str = "") -> str:
    """
    Phân loại email thành các category: needs_reply, schedule, fyi, spam
    
    Workflow:
    1. Tạo prompt cho Gemini AI với email details
    2. Parse JSON response từ AI
    3. Validate response format
    4. Fallback sang heuristic rules nếu AI fails
    
    Args:
        subject: Tiêu đề email
        body: Nội dung email
        sender: Địa chỉ người gửi (optional)
        
    Returns:
        String classification: "needs_reply", "schedule", "fyi", hoặc "spam"
    """
    try:
        # Tạo prompt cho AI classification
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
        
        # Gọi Gemini AI
        resp = get_client().models.generate_content(model=MODEL, contents=prompt)
        response_text = (resp.text or "").strip()
        
        # Parse JSON response - handle markdown code blocks
        try:
            # Remove markdown code block markers nếu có
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
            # Fallback: try to extract category from text nếu JSON parsing fails
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
        # Fallback heuristic khi model quota/exceptions xảy ra
        text = f"{subject}\n{body}".lower()
        
        # Simple rules để vẫn surface actionable emails
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

        # Apply heuristic rules
        if any(k in text for k in spam_keywords):
            return "spam"
        if any(k in text for k in schedule_keywords):
            return "schedule"
        if any(k in text for k in needs_reply_keywords):
            return "needs_reply"
        return "fyi"

def draft_reply(subject: str, body: str, tone: str, pref_hours: str, sender: str = "", vip_contacts: List[str] = None) -> str:
    """
    Tạo draft reply email sử dụng Gemini AI
    
    Workflow:
    1. Kiểm tra VIP status của sender
    2. Tạo prompt với context và preferences
    3. Gọi Gemini AI để generate reply
    4. Fallback sang generic reply nếu AI fails
    
    Args:
        subject: Tiêu đề email gốc
        body: Nội dung email gốc
        tone: Tone preference của user (e.g., "polite, concise")
        pref_hours: Preferred meeting hours
        sender: Địa chỉ người gửi
        vip_contacts: List VIP contacts (optional)
        
    Returns:
        Generated reply text, hoặc fallback message
    """
    try:
        # Kiểm tra VIP status
        vip_context = ""
        if vip_contacts and sender in vip_contacts:
            vip_context = " (This is a VIP contact - be extra professional and responsive)"
        
        # Tạo prompt cho AI
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
        
        # Gọi Gemini AI
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
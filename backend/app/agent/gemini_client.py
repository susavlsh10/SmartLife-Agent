import os
import google.generativeai as genai
from typing import Optional

# Initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not set. Chat functionality will not work.")


async def get_gemini_response(message: str) -> str:
    """Get response from Gemini AI model"""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. Please set it to use the chat feature."
        )

    try:
        # Use the Gemini Pro model
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # Generate response
        response = model.generate_content(message)
        
        if response and response.text:
            return response.text
        else:
            return "I apologize, but I couldn't generate a response. Please try again."
    except Exception as e:
        raise Exception(f"Error calling Gemini API: {str(e)}")


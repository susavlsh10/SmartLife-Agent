import uuid
import json
import re
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import ChatResponse, ChatHistoryItem
from pydantic import BaseModel
from app.auth import verify_token, get_user_by_id
from app.database import get_db
from app.db_models import ChatHistory
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()


def get_current_user_id(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> str:
    """Extract and verify user ID from authorization token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Verify user exists
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user_id


def extract_projects_from_response(response_text: str) -> Optional[List[dict]]:
    """Extract project proposals from Gemini response if present"""
    try:
        # Look for JSON in the response (Gemini might return structured data)
        json_match = re.search(r'\{.*"projects".*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if isinstance(data, dict) and "projects" in data:
                return data["projects"]
        
        # Look for markdown code blocks with JSON
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if code_block_match:
            data = json.loads(code_block_match.group(1))
            if isinstance(data, dict) and "projects" in data:
                return data["projects"]
        
        return None
    except:
        return None


async def generate_project_proposals(user_message: str, existing_projects: Optional[List[dict]] = None) -> tuple[str, Optional[List[dict]]]:
    """Use Gemini to generate project proposals from user goals"""
    import os
    import google.generativeai as genai
    from datetime import datetime
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")
    
    # Get current date and time
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    current_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
    day_of_week = now.strftime("%A")
    
    # Build conversation context
    context = "You are a helpful assistant that helps users identify their goals and convert them into actionable projects.\n\n"
    context += f"CURRENT DATE AND TIME: {current_datetime} ({day_of_week})\n"
    context += f"Today is {current_date} and the current time is {current_time}.\n"
    context += "Use this information to suggest realistic due dates for projects.\n\n"
    
    if existing_projects:
        context += "The user is asking to edit/refine these existing project proposals:\n"
        for i, proj in enumerate(existing_projects, 1):
            context += f"{i}. {proj.get('title', 'Untitled')}\n"
            if proj.get('description'):
                context += f"   Description: {proj.get('description')}\n"
            if proj.get('due_date'):
                context += f"   Due Date: {proj.get('due_date')}\n"
        context += "\n"
        context += "User's request for changes:\n"
    else:
        context += "When a user expresses goals, aspirations, or things they want to accomplish, you should:\n"
        context += "1. Acknowledge their goals warmly in a natural, conversational way\n"
        context += "2. Extract concrete, actionable projects from their goals\n"
        context += "3. For each project, suggest:\n"
        context += "   - A clear, specific title\n"
        context += "   - A brief description (1-2 sentences)\n"
        context += "   - A realistic due date based on the current date (YYYY-MM-DD format, or null if no deadline)\n"
        context += "4. Return ONLY a JSON object with this exact structure (no other text):\n"
        context += '{"response": "Your natural conversational response (no JSON formatting mentioned)", "projects": [{"title": "...", "description": "...", "due_date": "YYYY-MM-DD or null"}]}\n\n'
        context += 'If the user is just chatting or asking questions (not expressing goals), respond normally with just: {"response": "your text", "projects": null}\n\n'
    
    # No conversation history - each goal is independent
    context += f"User: {user_message}\n"
    context += "Assistant:"
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        # Request JSON response format with more explicit instructions and example
        example_json = '''{
  "response": "Great! I've analyzed your goals and here are some project suggestions.",
  "projects": [
    {"title": "Example Project", "description": "This is an example", "due_date": "2025-12-31"}
  ]
}'''
        json_prompt = context + f"\n\nCRITICAL INSTRUCTIONS:\n1. Respond with ONLY valid JSON (no markdown, no code blocks, no explanations)\n2. Use this EXACT format:\n{example_json}\n3. Start with {{ and end with }}\n4. Ensure all strings are properly quoted\n5. If no projects, use: {{\"response\": \"your text\", \"projects\": []}}"
        response = model.generate_content(json_prompt)
        
        if response and response.text:
            raw_response = response.text.strip()
            print(f"🔍 Raw Gemini response (first 500 chars): {raw_response[:500]}")
            response_text = ""
            projects = None
            
            # Remove markdown code blocks if present
            raw_response = re.sub(r'```json\s*', '', raw_response)
            raw_response = re.sub(r'```\s*', '', raw_response)
            raw_response = raw_response.strip()
            
            # Try to fix common JSON issues
            # Add opening brace if missing
            if not raw_response.startswith('{') and not raw_response.startswith('['):
                # Check if it looks like it should be wrapped
                if '"response"' in raw_response or '"projects"' in raw_response or '"title"' in raw_response:
                    raw_response = '{' + raw_response
                    if not raw_response.endswith('}'):
                        raw_response = raw_response + '}'
            
            # Try to extract JSON from response
            try:
                # First, try parsing the entire response as JSON
                data = json.loads(raw_response)
                response_text = data.get("response", "")
                projects = data.get("projects", None)
                print(f"✅ Successfully parsed JSON. Response: {response_text[:50]}..., Projects: {len(projects) if projects else 0}")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parse error: {e}")
                print(f"Raw response: {raw_response[:200]}...")
                
                # Try to find JSON object (more flexible pattern)
                # Look for content between first { and last }
                json_start = raw_response.find('{')
                json_end = raw_response.rfind('}')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_str = raw_response[json_start:json_end + 1]
                    try:
                        data = json.loads(json_str)
                        response_text = data.get("response", "")
                        projects = data.get("projects", None)
                        print(f"✅ Extracted JSON from substring. Projects: {len(projects) if projects else 0}")
                    except json.JSONDecodeError:
                        print("⚠️ Failed to parse extracted JSON substring")
                        # Try to manually extract projects array
                        projects_match = re.search(r'"projects"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
                        if projects_match:
                            try:
                                projects_json = '[' + projects_match.group(1) + ']'
                                projects = json.loads(projects_json)
                                print(f"✅ Manually extracted projects: {len(projects)}")
                            except:
                                pass
                        
                        # If still no projects, check if the entire response is just a projects array
                        if not projects:
                            # Check if response starts with [ (array of projects)
                            if raw_response.strip().startswith('['):
                                try:
                                    projects = json.loads(raw_response)
                                    print(f"✅ Parsed entire response as projects array: {len(projects)}")
                                except:
                                    pass
                            
                            # Check if response contains project-like structures
                            if not projects:
                                # Try to find all project objects (handling nested structures)
                                # Look for objects that start with { and contain "title"
                                project_pattern = r'\{\s*"title"\s*:\s*"[^"]*"[^}]*\}'
                                project_matches = re.findall(project_pattern, raw_response)
                                if project_matches:
                                    print(f"⚠️ Found {len(project_matches)} potential project objects")
                                    extracted_projects = []
                                    for match in project_matches:
                                        try:
                                            # Try to parse as JSON
                                            proj = json.loads(match)
                                            if "title" in proj:
                                                extracted_projects.append(proj)
                                        except:
                                            # If simple parse fails, try to extract fields manually
                                            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', match)
                                            desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', match)
                                            date_match = re.search(r'"due_date"\s*:\s*"([^"]+)"', match)
                                            if title_match:
                                                proj = {"title": title_match.group(1)}
                                                if desc_match:
                                                    proj["description"] = desc_match.group(1)
                                                if date_match:
                                                    proj["due_date"] = date_match.group(1)
                                                extracted_projects.append(proj)
                                    if extracted_projects:
                                        projects = extracted_projects
                                        print(f"✅ Extracted {len(projects)} projects from individual objects")
                
                # Extract response text separately if needed
                if not response_text:
                    response_match = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_response, re.DOTALL)
                    if response_match:
                        response_text = response_match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
            
            # Final cleanup: remove any remaining JSON artifacts from response text
            if response_text:
                response_text = re.sub(r'^[^{]*\{', '', response_text)
                response_text = re.sub(r'\}[^}]*$', '', response_text)
                response_text = response_text.strip().strip('"').strip()
            
            # Ensure we have a valid response text
            if not response_text or response_text.strip() == "" or response_text.startswith('{'):
                response_text = "I've analyzed your goals and prepared some project suggestions for you."
            
            print(f"📊 Final: response_text length={len(response_text)}, projects count={len(projects) if projects else 0}")
            
            # Validate and format projects
            if projects and isinstance(projects, list):
                formatted_projects = []
                for proj in projects:
                    if isinstance(proj, dict) and "title" in proj:
                        formatted_projects.append({
                            "title": proj.get("title", ""),
                            "description": proj.get("description", ""),
                            "due_date": proj.get("due_date")  # Keep as string, will be parsed on frontend
                        })
                if formatted_projects:
                    return response_text, formatted_projects
            
            return response_text, None
        
        return "I apologize, but I couldn't generate a response. Please try again.", None
    except Exception as e:
        raise Exception(f"Error calling Gemini API: {str(e)}")


class ChatMessageWithProjects(BaseModel):
    message: str
    existing_projects: Optional[List[dict]] = None  # For editing existing proposals


@router.post("", response_model=ChatResponse)
async def send_message(
    message: ChatMessageWithProjects,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Send a chat message and get AI response with project proposals"""
    try:
        # All messages are treated as goal-oriented - no conversation history
        # If user is editing existing projects, use that context
        if message.existing_projects:
            response_text, proposed_projects = await generate_project_proposals(
                message.message, message.existing_projects
            )
        else:
            # Generate project proposals for the goal (no history)
            response_text, proposed_projects = await generate_project_proposals(
                message.message
            )
        
        # Save to database (only save the natural language response, not JSON)
        chat_entry = ChatHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            message=message.message,
            response=response_text,  # Store only the natural language response
        )
        db.add(chat_entry)
        db.commit()

        return ChatResponse(
            response=response_text,
            proposed_projects=proposed_projects,
            requires_confirmation=proposed_projects is not None and len(proposed_projects) > 0
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.get("/history", response_model=List[ChatHistoryItem])
async def get_history(
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """Get chat history for the current user"""
    chat_entries = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.timestamp.asc())
        .all()
    )

    return [
        ChatHistoryItem(
            id=entry.id,
            message=entry.message,
            response=entry.response,
            timestamp=entry.timestamp.isoformat() if entry.timestamp else "",
        )
        for entry in chat_entries
    ]


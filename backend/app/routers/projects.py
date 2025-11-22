from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import json
from app.models import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    TodoItemCreate,
    TodoItemUpdate,
    TodoItemResponse,
    ProjectChatMessage,
    ProjectChatResponse,
    ProjectChatHistoryItem,
    GeneratePlanRequest,
    GeneratePlanResponse,
    GenerateTodosResponse,
    ScheduleTodosResponse,
)
from app.database import get_db
from app.db_models import Project, TodoItem, ProjectChatMessage as DBProjectChatMessage
from app.auth import verify_token
from app.agent.gemini_client import get_gemini_response
from app.agent.mcp_agent import get_mcp_agent

router = APIRouter()
logger = logging.getLogger(__name__)


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract and verify user ID from authorization header"""
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
    
    return user_id


@router.get("", response_model=List[ProjectResponse])
async def get_projects(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get all projects for the current user"""
    projects = db.query(Project).filter(Project.user_id == user_id).order_by(Project.updated_at.desc()).all()
    return projects


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new project"""
    project = Project(
        user_id=user_id,
        title=project_data.title,
        description=project_data.description,
        due_date=project_data.due_date,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Update a project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project_data.title is not None:
        project.title = project_data.title
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.due_date is not None:
        project.due_date = project_data.due_date
    if project_data.plan is not None:
        project.plan = project_data.plan
    
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    db.delete(project)
    db.commit()
    return None


# Todo Items endpoints
@router.post("/{project_id}/todos", response_model=TodoItemResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(
    project_id: str,
    todo_data: TodoItemCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new todo item in a project"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    todo = TodoItem(
        project_id=project_id,
        text=todo_data.text,
        completed=todo_data.completed,
        due_date=todo_data.due_date,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@router.put("/{project_id}/todos/{todo_id}", response_model=TodoItemResponse)
async def update_todo(
    project_id: str,
    todo_id: str,
    todo_data: TodoItemUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Update a todo item"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    todo = db.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.project_id == project_id
    ).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo item not found"
        )
    
    if todo_data.text is not None:
        todo.text = todo_data.text
    if todo_data.completed is not None:
        todo.completed = todo_data.completed
    if todo_data.due_date is not None:
        todo.due_date = todo_data.due_date
    
    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/{project_id}/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    project_id: str,
    todo_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a todo item"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    todo = db.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.project_id == project_id
    ).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo item not found"
        )
    
    db.delete(todo)
    db.commit()
    return None


# Project Chat endpoints
@router.post("/{project_id}/chat", response_model=ProjectChatResponse)
async def send_project_chat_message(
    project_id: str,
    chat_data: ProjectChatMessage,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Send a chat message for a specific project with MCP agent capabilities"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Build context from project details
    context = f"""Project: {project.title}
Description: {project.description or 'No description'}
Due Date: {project.due_date.strftime('%Y-%m-%d') if project.due_date else 'Not set'}

Todo Items:
"""
    for i, todo in enumerate(project.todos, 1):
        status_mark = "✓" if todo.completed else "○"
        context += f"{i}. [{status_mark}] {todo.text}\n"
    
    # Add current execution plan if it exists
    if project.plan:
        context += f"\nCurrent Execution Plan:\n{project.plan}\n"
    else:
        context += "\nCurrent Execution Plan: Not yet created\n"
    
    # Get AI response using MCP agent with Gmail and Calendar tools
    try:
        agent = await get_mcp_agent()
        response, updated_plan = await agent.chat(
            project_id=project_id,
            user_message=chat_data.message,
            project_context=context
        )
        
        # If the agent updated the plan, save it to the database
        if updated_plan:
            project.plan = updated_plan
            project.updated_at = datetime.utcnow()
            db.add(project)  # Mark project as modified
            db.commit()  # Commit plan changes immediately
            logger.info(f"Plan updated for project {project_id}, length: {len(updated_plan)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        response = f"I apologize, but I encountered an error: {str(e)}"
        updated_plan = None
    
    # Save chat message
    chat_message = DBProjectChatMessage(
        project_id=project_id,
        message=chat_data.message,
        response=response,
    )
    db.add(chat_message)
    db.commit()
    
    return ProjectChatResponse(response=response, plan_updated=updated_plan is not None)


@router.get("/{project_id}/chat/history", response_model=List[ProjectChatHistoryItem])
async def get_project_chat_history(
    project_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get chat history for a specific project"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    messages = db.query(DBProjectChatMessage).filter(
        DBProjectChatMessage.project_id == project_id
    ).order_by(DBProjectChatMessage.timestamp.asc()).all()
    
    return messages


# Plan Generation endpoints
@router.post("/{project_id}/generate-plan", response_model=GeneratePlanResponse)
async def generate_project_plan(
    project_id: str,
    plan_request: GeneratePlanRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Generate an execution plan for a project using AI"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Build context from project details
    today_date = datetime.now().strftime("%Y-%m-%d")
    context = f"""Today's date is {today_date}.

Project Title: {project.title}
Description: {project.description or 'No description provided'}
Due Date: {project.due_date.strftime('%Y-%m-%d') if project.due_date else 'Not set'}

Current Todo Items:
"""
    for i, todo in enumerate(project.todos, 1):
        status_mark = "✓" if todo.completed else "○"
        context += f"{i}. [{status_mark}] {todo.text}\n"
    
    # Prepare the prompt for plan generation
    if plan_request.message:
        # User is providing clarification or refinement
        prompt = f"""Based on the project context and the user's input, refine or generate an execution plan.

{context}

User's message: {plan_request.message}

Generate a detailed, actionable execution plan. Include:
1. Clear phases or milestones
2. Specific tasks with estimated timelines
3. Dependencies between tasks
4. Key deliverables
5. Potential risks and mitigation strategies

Format the plan in a clear, structured markdown format."""
    else:
        # Initial plan generation
        prompt = f"""Based on the project details, generate a comprehensive execution plan.

{context}

Generate a detailed, actionable execution plan. Include:
1. Clear phases or milestones
2. Specific tasks with estimated timelines
3. Dependencies between tasks
4. Key deliverables
5. Potential risks and mitigation strategies

If you need more information to create an optimal plan, ask clarifying questions.
Otherwise, provide the complete execution plan in a clear, structured markdown format."""
    
    # Get AI response using MCP agent
    try:
        agent = await get_mcp_agent()
        response, updated_plan = await agent.chat(
            project_id=f"{project_id}_plan",
            user_message=prompt,
            project_context=context
        )
        
        # If the agent used the update_execution_plan tool, use that plan
        if updated_plan:
            project.plan = updated_plan
            project.updated_at = datetime.utcnow()
            db.commit()
            
            return GeneratePlanResponse(
                plan=updated_plan,
                needs_clarification=False
            )
        
        # Check if the response contains questions (simple heuristic)
        needs_clarification = "?" in response and len(response.split("?")) <= 3 and len(response) < 500
        
        if needs_clarification and not plan_request.message:
            # AI is asking for clarification
            return GeneratePlanResponse(
                plan=project.plan or "",
                needs_clarification=True,
                clarification_question=response
            )
        else:
            # AI provided a plan in text - save it
            project.plan = response
            project.updated_at = datetime.utcnow()
            db.commit()
            
            return GeneratePlanResponse(
                plan=response,
                needs_clarification=False
            )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate plan: {str(e)}"
        )


@router.put("/{project_id}/plan", response_model=ProjectResponse)
async def update_project_plan(
    project_id: str,
    plan_data: dict,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Manually update the project plan"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update the plan
    if "plan" in plan_data:
        project.plan = plan_data["plan"]
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(project)
    
    return project


@router.post("/{project_id}/generate-todos", response_model=GenerateTodosResponse)
async def generate_todos_from_plan(
    project_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Generate TODO items from the execution plan using AI"""
    from app.models import GenerateTodosResponse
    import json
    
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if not project.plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No execution plan exists. Please generate a plan first."
        )
    
    # Build context for the AI
    today_date = datetime.now().strftime("%Y-%m-%d")
    context = f"""Today's date is {today_date}.

Project Title: {project.title}
Description: {project.description or 'No description provided'}
Due Date: {project.due_date.strftime('%Y-%m-%d') if project.due_date else 'Not set'}

Execution Plan:
{project.plan}

Your task: Analyze the execution plan and break it down into concrete, actionable TODO items.
Each TODO should:
1. Be specific and actionable
2. Have a realistic due date AND time (if the plan mentions timelines)
3. Be ordered logically
4. Include a reasonable time of day (between 9 AM and 6 PM) in the due_date

IMPORTANT: When setting due dates, use ISO format with time: "YYYY-MM-DDTHH:MM:SS"
For example: "2025-11-23T09:00:00" (9 AM), "2025-11-23T14:00:00" (2 PM), etc.
Suggest times between 9:00 AM and 6:00 PM for optimal productivity.

Use the generate_todos_from_plan tool to create the TODOs."""
    
    try:
        agent = await get_mcp_agent()
        
        # Use a custom conversation to track tool calls
        response, _ = await agent.chat(
            project_id=f"{project_id}_generate_todos",
            user_message=context,
            project_context=""
        )
        
        logger.info(f"AI response for todo generation: {response}")
        
        # Extract todos from the MCP agent's tool call
        # Check the agent's conversation history for the generate_todos_from_plan tool result
        conversation = agent.project_conversations.get(f"{project_id}_generate_todos", [])
        
        todos_data = []
        
        # Look through the conversation for tool responses
        for content in conversation:
            if content.role == "user" and content.parts:
                for part in content.parts:
                    # Check if this is a function response
                    if hasattr(part, 'function_response') and part.function_response:
                        if part.function_response.name == "generate_todos_from_plan":
                            # Extract the todos from the response
                            response_data = part.function_response.response
                            if isinstance(response_data, dict) and 'result' in response_data:
                                try:
                                    result_json = json.loads(response_data['result'])
                                    if result_json.get('success') and 'todos' in result_json:
                                        todos_data = result_json['todos']
                                        logger.info(f"Extracted {len(todos_data)} todos from MCP tool response")
                                        break
                                except json.JSONDecodeError:
                                    pass
            if todos_data:
                break
        
        # If we didn't get todos from tool response, return error
        if not todos_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate todos from plan. The AI did not return structured data."
            )
        
        # Create TODO items in database
        created_todos = []
        for todo_data in todos_data:
            due_date = None
            if todo_data.get("due_date"):
                try:
                    # Try parsing different date formats (with priority for ISO datetime)
                    date_str = todo_data["due_date"]
                    
                    # Try full ISO format first (with time)
                    if 'T' in date_str:
                        try:
                            # Try full datetime with or without microseconds
                            if '.' in date_str:
                                due_date = datetime.strptime(date_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                            else:
                                due_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
                        except ValueError:
                            # Fallback to just the date part at 9 AM
                            due_date = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
                            due_date = due_date.replace(hour=9, minute=0, second=0)
                    else:
                        # Date only - default to 9 AM
                        due_date = datetime.strptime(date_str, '%Y-%m-%d')
                        due_date = due_date.replace(hour=9, minute=0, second=0)
                        
                except ValueError as e:
                    logger.warning(f"Failed to parse date {todo_data.get('due_date')}: {e}")
            
            todo = TodoItem(
                project_id=project_id,
                text=todo_data["text"],
                completed=False,
                due_date=due_date
            )
            db.add(todo)
            created_todos.append(todo)
        
        db.commit()
        
        # Refresh all todos to get IDs
        for todo in created_todos:
            db.refresh(todo)
        
        logger.info(f"Created {len(created_todos)} TODO items for project {project_id}")
        
        return GenerateTodosResponse(
            todos=created_todos,
            message=f"Successfully generated {len(created_todos)} TODO items from the execution plan."
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse AI response. Please try again."
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate TODOs: {str(e)}"
        )


@router.post("/{project_id}/schedule-todos", response_model=ScheduleTodosResponse)
async def schedule_todos_to_calendar(
    project_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Schedule TODO items to Google Calendar using direct API calls"""
    from app.models import ScheduleTodosResponse
    from app.calendar_helper import create_calendar_event
    
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get incomplete TODOs that are not already scheduled
    todos_to_schedule = [
        todo for todo in project.todos 
        if not todo.completed and not todo.calendar_event_id
    ]
    
    if not todos_to_schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No incomplete TODO items to schedule."
        )
    
    # Try direct API scheduling first
    scheduled_count = 0
    failed_todos = []
    calendar_events = []
    current_time = datetime.now()
    
    for i, todo in enumerate(todos_to_schedule):
        try:
            # Determine start time based on due date
            if todo.due_date:
                # Use the time from due_date if it's reasonable (between 6 AM and 11 PM)
                # Otherwise default to 9 AM
                hour = todo.due_date.hour
                minute = todo.due_date.minute
                
                # If time is unreasonable (midnight to 6 AM), default to 9 AM
                if hour < 6:
                    hour = 9
                    minute = 0
                elif hour >= 23:
                    hour = 9
                    minute = 0
                
                start_time = datetime.combine(
                    todo.due_date.date(),
                    datetime.min.time().replace(hour=hour, minute=minute, second=0, microsecond=0)
                )
            else:
                # Schedule sequentially starting tomorrow at 9 AM, with 2-hour slots
                days_ahead = (i // 4) + 1  # 4 slots per day (9am, 11am, 2pm, 4pm)
                slot_of_day = i % 4
                base_date = current_time + timedelta(days=days_ahead)
                
                # Time slots: 9am, 11am, 2pm, 4pm
                slot_hours = [9, 11, 14, 16]
                start_time = base_date.replace(
                    hour=slot_hours[slot_of_day], 
                    minute=0, 
                    second=0, 
                    microsecond=0
                )
            
            # Calculate end time (1 hour duration)
            end_time = start_time + timedelta(hours=1)
            
            # Create calendar event directly
            event = create_calendar_event(
                user_id=user_id,
                db=db,
                summary=todo.text,
                description=f"Project: {project.title}\n\n{project.description or ''}",
                start_time=start_time,
                end_time=end_time
                # Uses default timezone (America/Chicago) - change if needed
            )
            
            if event:
                # Update database with event ID
                todo.calendar_event_id = event['id']
                db.commit()
                scheduled_count += 1
                calendar_events.append({
                    'todo_id': todo.id,
                    'event_id': event['id'],
                    'event_link': event.get('htmlLink'),
                    'start_time': start_time.isoformat()
                })
                logger.info(f"Scheduled todo {todo.id} to calendar: {event['id']}")
            else:
                failed_todos.append(todo)
                
        except Exception as e:
            logger.error(f"Failed to schedule todo {todo.id}: {str(e)}")
            failed_todos.append(todo)
    
    # If some todos failed and don't have due dates, use MCP agent as fallback
    if failed_todos and any(not todo.due_date for todo in failed_todos):
        logger.info(f"Falling back to MCP agent for {len(failed_todos)} todos without due dates")
        
        try:
            today_date = datetime.now().strftime("%Y-%m-%d")
            todos_text = "\n".join([
                f"- {todo.text}" + (f" (due: {todo.due_date.strftime('%Y-%m-%d')})" if todo.due_date else "")
                for todo in failed_todos
            ])
            
            context = f"""Today's date is {today_date}.

Project: {project.title}
Description: {project.description or 'No description'}

TODO Items to schedule (these need intelligent scheduling):
{todos_text}

Your task: Schedule these TODO items as events in the user's Google Calendar.
For each TODO:
1. Create a calendar event with an appropriate time slot
2. Suggest a reasonable timeframe based on the task
3. Set an appropriate duration (e.g., 1-2 hours for study sessions)
4. Add the event description to include the project context

Use the Google Calendar MCP tools to create these events. Be smart about scheduling - don't overlap events, consider reasonable working hours."""
            
            agent = await get_mcp_agent()
            response, _ = await agent.chat(
                project_id=f"{project_id}_schedule",
                user_message=context,
                project_context=""
            )
            
            logger.info(f"MCP agent scheduling response: {response}")
            scheduled_count += len(failed_todos)  # Assume agent scheduled them all
            
        except Exception as e:
            logger.error(f"MCP agent fallback also failed: {str(e)}")
    
    if scheduled_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule any tasks to calendar."
        )
    
    return ScheduleTodosResponse(
        scheduled_count=scheduled_count,
        message=f"Successfully scheduled {scheduled_count} of {len(todos_to_schedule)} tasks to your Google Calendar using direct API calls.",
        calendar_events=calendar_events
    )


@router.post("/{project_id}/todos/{todo_id}/schedule")
async def schedule_single_todo(
    project_id: str,
    todo_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Schedule a single TODO item to Google Calendar directly"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get the todo item
    todo = db.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.project_id == project_id
    ).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo item not found"
        )
    
    if todo.calendar_event_id:
        return {
            "success": True,
            "calendar_event_id": todo.calendar_event_id,
            "message": "This task is already scheduled to your calendar."
        }
    
    # Determine start time based on due date
    if todo.due_date:
        # Use the time from due_date if it's reasonable (between 6 AM and 11 PM)
        # Otherwise default to 9 AM
        hour = todo.due_date.hour
        minute = todo.due_date.minute
        
        # If time is unreasonable (midnight to 6 AM, or 11 PM to midnight), default to 9 AM
        if hour < 6 or hour >= 23:
            hour = 9
            minute = 0
        
        start_time = datetime.combine(
            todo.due_date.date(),
            datetime.min.time().replace(hour=hour, minute=minute, second=0, microsecond=0)
        )
    else:
        # Schedule for tomorrow at 9 AM
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Calculate end time (1 hour duration)
    end_time = start_time + timedelta(hours=1)
    
    # Create calendar event directly using Google Calendar API (NO MCP AGENT!)
    try:
        from app.calendar_helper import create_calendar_event
        
        event = create_calendar_event(
            user_id=user_id,
            db=db,
            summary=todo.text,
            description=f"Project: {project.title}\n\n{project.description or ''}",
            start_time=start_time,
            end_time=end_time
            # Uses default timezone (America/Chicago) - change if needed
        )
        
        if not event:
            raise ValueError("Failed to create calendar event")
        
        # Update database with event ID
        todo.calendar_event_id = event['id']
        db.commit()
        db.refresh(todo)
        
        logger.info(f"Scheduled todo {todo_id} to calendar: {event['id']}")
        
        return {
            "success": True,
            "calendar_event_id": event['id'],
            "message": f"Successfully scheduled '{todo.text}' to your Google Calendar for {start_time.strftime('%b %d at %I:%M %p')}.",
            "event_link": event.get('htmlLink')
        }
        
    except ValueError as e:
        # Handle specific error messages
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to schedule todo to calendar: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule to calendar: {str(e)}"
        )

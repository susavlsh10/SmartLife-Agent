from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
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
)
from app.database import get_db
from app.db_models import Project, TodoItem, ProjectChatMessage as DBProjectChatMessage
from app.auth import verify_token
from app.agent.gemini_client import get_gemini_response
from app.agent.mcp_agent import get_mcp_agent

router = APIRouter()


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
    
    # Get AI response using MCP agent with Gmail and Calendar tools
    try:
        agent = await get_mcp_agent(user_id=user_id)
        response = await agent.chat(
            project_id=project_id,
            user_message=chat_data.message,
            project_context=context
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        response = f"I apologize, but I encountered an error: {str(e)}"
    
    # Save chat message
    chat_message = DBProjectChatMessage(
        project_id=project_id,
        message=chat_data.message,
        response=response,
    )
    db.add(chat_message)
    db.commit()
    
    return ProjectChatResponse(response=response)


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

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None


class AuthResponse(BaseModel):
    user: UserResponse
    token: str


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    proposed_projects: Optional[List[dict]] = None  # List of proposed projects with title, description, due_date
    requires_confirmation: bool = False  # Whether user needs to confirm project creation


class ChatHistoryItem(BaseModel):
    id: str
    message: str
    response: str
    timestamp: str


# Project Models
class TodoItemCreate(BaseModel):
    text: str
    completed: bool = False


class TodoItemUpdate(BaseModel):
    text: Optional[str] = None
    completed: Optional[bool] = None


class TodoItemResponse(BaseModel):
    id: str
    text: str
    completed: bool
    order_index: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    
    @field_validator('due_date')
    @classmethod
    def parse_due_date(cls, v):
        if v is None or v == '':
            return None
        if isinstance(v, datetime):
            return v
        # Try to parse the date string
        try:
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        except:
            return datetime.strptime(v, '%Y-%m-%d')


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    
    @field_validator('due_date')
    @classmethod
    def parse_due_date(cls, v):
        if v is None or v == '':
            return None
        if isinstance(v, datetime):
            return v
        # Try to parse the date string
        try:
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        except:
            return datetime.strptime(v, '%Y-%m-%d')


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    todos: List[TodoItemResponse] = []

    class Config:
        from_attributes = True


class ProjectChatMessage(BaseModel):
    message: str


class ProjectChatResponse(BaseModel):
    response: str


class ProjectChatHistoryItem(BaseModel):
    id: str
    message: str
    response: str
    timestamp: datetime

    class Config:
        from_attributes = True


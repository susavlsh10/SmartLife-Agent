import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chat_history = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    google_calendar_credentials = relationship("GoogleCalendarCredentials", back_populates="user", uselist=False, cascade="all, delete-orphan")
    user_preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship to user
    user = relationship("User", back_populates="chat_history")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="projects")
    todos = relationship("TodoItem", back_populates="project", cascade="all, delete-orphan")
    chat_messages = relationship("ProjectChatMessage", back_populates="project", cascade="all, delete-orphan")


class TodoItem(Base):
    __tablename__ = "todo_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    order_index = Column(String, nullable=True)

    # Relationship to project
    project = relationship("Project", back_populates="todos")


class ProjectChatMessage(Base):
    __tablename__ = "project_chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship to project
    project = relationship("Project", back_populates="chat_messages")


class GoogleCalendarCredentials(Base):
    __tablename__ = "google_calendar_credentials"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    credentials_json = Column(Text, nullable=False)  # Store credentials.json content
    token_json = Column(Text, nullable=True)  # Store token.json content
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to user
    user = relationship("User", back_populates="google_calendar_credentials")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Work/Study time preferences
    work_study_weekdays = Column(String, nullable=True)  # e.g., "9-17" for 9am-5pm
    work_study_weekends = Column(String, nullable=True)  # e.g., "any" or "10-14"
    work_study_all_time = Column(Boolean, default=False)  # If true, available all time
    
    # Gym/Activity time preferences
    gym_activity_weekdays = Column(String, nullable=True)
    gym_activity_weekends = Column(String, nullable=True)
    gym_activity_all_time = Column(Boolean, default=False)
    
    # Personal goals time preferences
    personal_goals_weekdays = Column(String, nullable=True)
    personal_goals_weekends = Column(String, nullable=True)
    personal_goals_all_time = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to user
    user = relationship("User", back_populates="user_preferences")


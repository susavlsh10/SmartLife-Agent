import json
from fastapi import APIRouter, HTTPException, status, Depends, Header, Query
from typing import Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.db_models import User, GoogleCalendarCredentials, UserPreferences
from app.auth import verify_token, get_user_by_id, hash_password, verify_password
from app.google_oauth import (
    get_authorization_url,
    exchange_code_for_token,
    get_user_email_from_token,
    refresh_token_if_needed,
)
import os

router = APIRouter()


# Pydantic models for requests/responses
class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class TimePreference(BaseModel):
    weekdays: Optional[str] = None
    weekends: Optional[str] = None
    all_time: bool = False


class UserPreferencesUpdate(BaseModel):
    work_study: TimePreference
    gym_activity: TimePreference
    personal_goals: TimePreference


class GoogleCalendarStatusResponse(BaseModel):
    connected: bool
    email: Optional[str] = None


class UserPreferencesResponse(BaseModel):
    work_study: TimePreference
    gym_activity: TimePreference
    personal_goals: TimePreference


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
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

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.post("/password", status_code=status.HTTP_200_OK)
async def update_password(
    password_data: PasswordUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user password"""
    # Verify current password
    if not verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Validate new password
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long",
        )

    # Update password
    user.password_hash = hash_password(password_data.new_password)
    db.commit()

    return {"message": "Password updated successfully"}


@router.get("/google-calendar/status", response_model=GoogleCalendarStatusResponse)
async def get_google_calendar_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if Google Calendar is connected"""
    credentials = db.query(GoogleCalendarCredentials).filter(
        GoogleCalendarCredentials.user_id == user.id
    ).first()

    if credentials and credentials.token_json:
        try:
            # Try to refresh token if needed
            refreshed_token = refresh_token_if_needed(credentials.token_json)
            if refreshed_token and refreshed_token != credentials.token_json:
                credentials.token_json = refreshed_token
                db.commit()
            
            # Get user email
            email = get_user_email_from_token(credentials.token_json)
            return GoogleCalendarStatusResponse(connected=True, email=email)
        except Exception as e:
            print(f"Error checking calendar status: {e}")
            return GoogleCalendarStatusResponse(connected=False)
    
    return GoogleCalendarStatusResponse(connected=False)


@router.get("/google-calendar/authorize")
async def get_google_calendar_authorization_url(
    redirect_uri: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
):
    """Get Google Calendar OAuth authorization URL"""
    try:
        # Use user ID as state to verify on callback
        state = user.id
        auth_url = get_authorization_url(redirect_uri=redirect_uri, state=state)
        return {"authorization_url": auth_url, "state": state}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate authorization URL: {str(e)}",
        )


@router.get("/google-calendar/callback")
async def google_calendar_oauth_callback(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    redirect_uri: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Handle Google Calendar OAuth callback"""
    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing state parameter",
        )

    # Verify user from state
    user = get_user_by_id(db, state)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid state parameter",
        )

    try:
        # Exchange code for token
        token_data = exchange_code_for_token(code, redirect_uri)
        token_json = json.dumps(token_data)

        # Get user email
        email = get_user_email_from_token(token_json)

        # Store or update credentials
        existing = db.query(GoogleCalendarCredentials).filter(
            GoogleCalendarCredentials.user_id == user.id
        ).first()

        if existing:
            existing.token_json = token_json
            # Store minimal client config if needed
            if not existing.credentials_json:
                existing.credentials_json = json.dumps({
                    "client_id": token_data.get("client_id"),
                    "client_secret": token_data.get("client_secret"),
                })
            db.commit()
        else:
            new_credentials = GoogleCalendarCredentials(
                user_id=user.id,
                credentials_json=json.dumps({
                    "client_id": token_data.get("client_id"),
                    "client_secret": token_data.get("client_secret"),
                }),
                token_json=token_json,
            )
            db.add(new_credentials)
            db.commit()

        return {
            "message": "Google Calendar connected successfully",
            "email": email,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete OAuth flow: {str(e)}",
        )


@router.delete("/google-calendar/disconnect", status_code=status.HTTP_200_OK)
async def disconnect_google_calendar(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect Google Calendar"""
    credentials = db.query(GoogleCalendarCredentials).filter(
        GoogleCalendarCredentials.user_id == user.id
    ).first()

    if credentials:
        db.delete(credentials)
        db.commit()

    return {"message": "Google Calendar disconnected successfully"}


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user preferences"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == user.id
    ).first()

    if not preferences:
        # Return default preferences
        default = TimePreference()
        return UserPreferencesResponse(
            work_study=default,
            gym_activity=default,
            personal_goals=default,
        )

    return UserPreferencesResponse(
        work_study=TimePreference(
            weekdays=preferences.work_study_weekdays,
            weekends=preferences.work_study_weekends,
            all_time=preferences.work_study_all_time,
        ),
        gym_activity=TimePreference(
            weekdays=preferences.gym_activity_weekdays,
            weekends=preferences.gym_activity_weekends,
            all_time=preferences.gym_activity_all_time,
        ),
        personal_goals=TimePreference(
            weekdays=preferences.personal_goals_weekdays,
            weekends=preferences.personal_goals_weekends,
            all_time=preferences.personal_goals_all_time,
        ),
    )


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    preferences_data: UserPreferencesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user preferences"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == user.id
    ).first()

    if not preferences:
        preferences = UserPreferences(user_id=user.id)
        db.add(preferences)

    # Update work/study preferences
    preferences.work_study_weekdays = preferences_data.work_study.weekdays
    preferences.work_study_weekends = preferences_data.work_study.weekends
    preferences.work_study_all_time = preferences_data.work_study.all_time

    # Update gym/activity preferences
    preferences.gym_activity_weekdays = preferences_data.gym_activity.weekdays
    preferences.gym_activity_weekends = preferences_data.gym_activity.weekends
    preferences.gym_activity_all_time = preferences_data.gym_activity.all_time

    # Update personal goals preferences
    preferences.personal_goals_weekdays = preferences_data.personal_goals.weekdays
    preferences.personal_goals_weekends = preferences_data.personal_goals.weekends
    preferences.personal_goals_all_time = preferences_data.personal_goals.all_time

    db.commit()
    db.refresh(preferences)

    return UserPreferencesResponse(
        work_study=TimePreference(
            weekdays=preferences.work_study_weekdays,
            weekends=preferences.work_study_weekends,
            all_time=preferences.work_study_all_time,
        ),
        gym_activity=TimePreference(
            weekdays=preferences.gym_activity_weekdays,
            weekends=preferences.gym_activity_weekends,
            all_time=preferences.gym_activity_all_time,
        ),
        personal_goals=TimePreference(
            weekdays=preferences.personal_goals_weekdays,
            weekends=preferences.personal_goals_weekends,
            all_time=preferences.personal_goals_all_time,
        ),
    )


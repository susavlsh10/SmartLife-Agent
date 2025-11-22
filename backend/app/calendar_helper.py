"""
Google Calendar Helper
Direct API calls to Google Calendar without using MCP agent
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from app.db_models import GoogleCalendarCredentials

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_user_credentials(user_id: str, db: Session) -> Optional[Credentials]:
    """Get Google Calendar credentials for a user"""
    try:
        # Get credentials from database
        creds_record = db.query(GoogleCalendarCredentials).filter(
            GoogleCalendarCredentials.user_id == user_id
        ).first()
        
        if not creds_record or not creds_record.token_json:
            logger.warning(f"No calendar credentials found for user {user_id}")
            return None
        
        # Parse token JSON
        token_data = json.loads(creds_record.token_json)
        
        # Create credentials object
        credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", SCOPES)
        )
        
        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            logger.info(f"Refreshing expired token for user {user_id}")
            credentials.refresh(Request())
            
            # Update token in database
            token_data["token"] = credentials.token
            creds_record.token_json = json.dumps(token_data)
            db.commit()
        
        return credentials
        
    except Exception as e:
        logger.error(f"Error getting credentials for user {user_id}: {str(e)}")
        return None


def create_calendar_event(
    user_id: str,
    db: Session,
    summary: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
    timezone: str = 'America/Chicago'  # Default to US Central Time
) -> Optional[Dict[str, Any]]:
    """
    Create a calendar event directly using Google Calendar API
    
    Args:
        user_id: User's ID
        db: Database session
        summary: Event title
        description: Event description
        start_time: Event start datetime (naive datetime, will be treated as local time)
        end_time: Event end datetime (naive datetime, will be treated as local time)
        timezone: Timezone for the event (default: America/Chicago)
    
    Returns:
        Event data dict with 'id', 'htmlLink', etc. or None if failed
    """
    try:
        # Get user credentials
        credentials = get_user_credentials(user_id, db)
        if not credentials:
            raise ValueError("Google Calendar not connected for this user")
        
        # Build Calendar API service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Format datetime for Google Calendar API
        # Google Calendar expects ISO format with timezone specified
        # If datetime is naive (no tzinfo), treat it as local time in specified timezone
        start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_iso = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Create event body
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_iso,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_iso,
                'timeZone': timezone,
            },
            'reminders': {
                'useDefault': True,
            },
        }
        
        # Call Google Calendar API
        logger.info(f"Creating calendar event for user {user_id}: {summary}")
        created_event = service.events().insert(
            calendarId='primary',
            body=event
        ).execute()
        
        logger.info(f"Successfully created event: {created_event.get('id')}")
        
        return {
            'id': created_event.get('id'),
            'htmlLink': created_event.get('htmlLink'),
            'summary': created_event.get('summary'),
            'start': created_event.get('start'),
            'end': created_event.get('end'),
        }
        
    except HttpError as e:
        logger.error(f"Google Calendar API error: {str(e)}")
        if e.resp.status == 401:
            raise ValueError("Google Calendar authentication failed. Please reconnect.")
        elif e.resp.status == 403:
            raise ValueError("Permission denied. Please grant calendar access.")
        else:
            raise ValueError(f"Failed to create calendar event: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error creating calendar event: {str(e)}")
        raise ValueError(f"Failed to create calendar event: {str(e)}")


def delete_calendar_event(
    user_id: str,
    db: Session,
    event_id: str
) -> bool:
    """
    Delete a calendar event
    
    Args:
        user_id: User's ID
        db: Database session
        event_id: Google Calendar event ID
    
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        credentials = get_user_credentials(user_id, db)
        if not credentials:
            raise ValueError("Google Calendar not connected for this user")
        
        service = build('calendar', 'v3', credentials=credentials)
        
        logger.info(f"Deleting calendar event {event_id} for user {user_id}")
        service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()
        
        logger.info(f"Successfully deleted event: {event_id}")
        return True
        
    except HttpError as e:
        logger.error(f"Google Calendar API error while deleting: {str(e)}")
        if e.resp.status == 404:
            logger.warning(f"Event {event_id} not found (may already be deleted)")
            return True  # Consider it deleted
        return False
    
    except Exception as e:
        logger.error(f"Error deleting calendar event: {str(e)}")
        return False


def update_calendar_event(
    user_id: str,
    db: Session,
    event_id: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    timezone: str = 'UTC'
) -> Optional[Dict[str, Any]]:
    """
    Update an existing calendar event
    
    Args:
        user_id: User's ID
        db: Database session
        event_id: Google Calendar event ID
        summary: New event title (optional)
        description: New event description (optional)
        start_time: New start datetime (optional)
        end_time: New end datetime (optional)
        timezone: Timezone (default: UTC)
    
    Returns:
        Updated event data or None if failed
    """
    try:
        credentials = get_user_credentials(user_id, db)
        if not credentials:
            raise ValueError("Google Calendar not connected for this user")
        
        service = build('calendar', 'v3', credentials=credentials)
        
        # Get existing event
        event = service.events().get(
            calendarId='primary',
            eventId=event_id
        ).execute()
        
        # Update fields
        if summary:
            event['summary'] = summary
        if description:
            event['description'] = description
        if start_time:
            event['start'] = {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            }
        if end_time:
            event['end'] = {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            }
        
        # Update event
        logger.info(f"Updating calendar event {event_id} for user {user_id}")
        updated_event = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event
        ).execute()
        
        logger.info(f"Successfully updated event: {event_id}")
        
        return {
            'id': updated_event.get('id'),
            'htmlLink': updated_event.get('htmlLink'),
            'summary': updated_event.get('summary'),
            'start': updated_event.get('start'),
            'end': updated_event.get('end'),
        }
        
    except HttpError as e:
        logger.error(f"Google Calendar API error while updating: {str(e)}")
        raise ValueError(f"Failed to update calendar event: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error updating calendar event: {str(e)}")
        raise ValueError(f"Failed to update calendar event: {str(e)}")

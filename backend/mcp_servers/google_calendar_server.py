import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Sequence

import pytz
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import EmbeddedResource, ImageContent, Resource, TextContent, Tool

# Ensure backend root is on sys.path for `import app.*`
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.db_models import GoogleCalendarCredentials

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Load environment variables
load_dotenv()

DEFAULT_CALENDAR_USER_ID = os.getenv('CALENDAR_USER_ID')

class GoogleCalendarServer:
    def __init__(self, user_id: Optional[str] = None):
        self.server = Server("google-calendar")
        self.service = None
        # Set your local timezone - adjust this to your actual timezone
        self.local_timezone =  pytz.timezone('America/Chicago')
        # Or use: pytz.timezone('America/Los_Angeles')  # PST/PDT
        self.user_id = user_id or DEFAULT_CALENDAR_USER_ID
        self._setup_tools()
        
    def _setup_tools(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="schedule_meeting",
                    description="Schedule a meeting in Google Calendar",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Meeting title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Meeting description (optional)"
                            },
                            "start_datetime": {
                                "type": "string",
                                "description": "Start time in ISO format (e.g., '2024-01-15T10:00:00')"
                            },
                            "end_datetime": {
                                "type": "string",
                                "description": "End time in ISO format (e.g., '2024-01-15T11:00:00')"
                            },
                            "attendees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of email addresses of attendees"
                            },
                            "location": {
                                "type": "string",
                                "description": "Meeting location (optional)"
                            }
                        },
                        "required": ["title", "start_datetime", "end_datetime"]
                    }
                ),
                Tool(
                    name="list_upcoming_events",
                    description="List upcoming events from Google Calendar",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of events to return (default: 10)",
                                "minimum": 1,
                                "maximum": 50
                            },
                            "days_ahead": {
                                "type": "integer",
                                "description": "Number of days ahead to look for events (default: 7)",
                                "minimum": 1,
                                "maximum": 365
                            }
                        }
                    }
                ),
                Tool(
                    name="find_free_time",
                    description="Find free time slots in calendar",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Date to check in YYYY-MM-DD format"
                            },
                            "duration_minutes": {
                                "type": "integer",
                                "description": "Duration of the meeting in minutes",
                                "minimum": 15,
                                "maximum": 480
                            },
                            "start_hour": {
                                "type": "integer",
                                "description": "Earliest hour to consider (0-23, default: 9)",
                                "minimum": 0,
                                "maximum": 23
                            },
                            "end_hour": {
                                "type": "integer",
                                "description": "Latest hour to consider (0-23, default: 17)",
                                "minimum": 0,
                                "maximum": 23
                            }
                        },
                        "required": ["date", "duration_minutes"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
            if not self.service:
                await self._authenticate()
                
            if name == "schedule_meeting":
                return await self._schedule_meeting(arguments)
            elif name == "list_upcoming_events":
                return await self._list_upcoming_events(arguments)
            elif name == "find_free_time":
                return await self._find_free_time(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _authenticate(self):
        """Authenticate with Google Calendar API using credentials stored in the database"""

        with SessionLocal() as session:
            query = session.query(GoogleCalendarCredentials)
            if self.user_id:
                credentials_entry = query.filter(GoogleCalendarCredentials.user_id == self.user_id).first()
            else:
                credentials_entry = query.first()

            if not credentials_entry or not credentials_entry.token_json:
                raise RuntimeError(
                    "Google Calendar is not connected. Please connect your calendar via the Settings page."
                )

            token_data = json.loads(credentials_entry.token_json)
            credentials_info = {}
            if credentials_entry.credentials_json:
                try:
                    credentials_info = json.loads(credentials_entry.credentials_json)
                except json.JSONDecodeError:
                    credentials_info = {}

            client_id = (
                token_data.get('client_id')
                or credentials_info.get('client_id')
                or os.getenv('GOOGLE_CLIENT_ID')
            )
            client_secret = (
                token_data.get('client_secret')
                or credentials_info.get('client_secret')
                or os.getenv('GOOGLE_CLIENT_SECRET')
            )
            token_uri = token_data.get('token_uri') or 'https://oauth2.googleapis.com/token'

            if not client_id or not client_secret:
                raise RuntimeError(
                    "Google OAuth credentials are not configured. Please ensure GOOGLE_CLIENT_ID and "
                    "GOOGLE_CLIENT_SECRET are set in the environment."
                )

            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=token_data.get('scopes', SCOPES),
            )

            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    try:
                        print("Refreshing Google Calendar access token...")
                        creds.refresh(Request())
                        token_data['token'] = creds.token
                        if creds.expiry:
                            token_data['expiry'] = creds.expiry.isoformat()
                        credentials_entry.token_json = json.dumps(token_data)
                        session.commit()
                        print("✅ Token refreshed successfully")
                    except Exception as refresh_error:
                        raise RuntimeError(
                            "Failed to refresh Google Calendar access token. Please reconnect your calendar via the "
                            "Settings page."
                        ) from refresh_error
                else:
                    raise RuntimeError(
                        "Stored Google Calendar token is invalid or expired. Please reconnect your calendar via the "
                        "Settings page."
                    )

        self.service = build('calendar', 'v3', credentials=creds)

    async def _schedule_meeting(self, args: dict) -> Sequence[TextContent]:
        try:
            # Parse the datetime strings and assume they're in local timezone if no timezone info
            start_dt_str = args['start_datetime']
            end_dt_str = args['end_datetime']
            
            # Parse datetime
            try:
                start_dt = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))
            except:
                # If no timezone info, assume local timezone
                start_dt = datetime.fromisoformat(start_dt_str)
                start_dt = self.local_timezone.localize(start_dt)
            
            try:
                end_dt = datetime.fromisoformat(end_dt_str.replace('Z', '+00:00'))
            except:
                # If no timezone info, assume local timezone
                end_dt = datetime.fromisoformat(end_dt_str)
                end_dt = self.local_timezone.localize(end_dt)
            
            event = {
                'summary': args['title'],
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': str(self.local_timezone),  # Use local timezone
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': str(self.local_timezone),  # Use local timezone
                },
            }
            
            # Add optional fields
            if 'description' in args:
                event['description'] = args['description']
            if 'location' in args:
                event['location'] = args['location']
            if 'attendees' in args and args['attendees']:
                event['attendees'] = [{'email': email} for email in args['attendees']]

            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all' if 'attendees' in event else 'none'
            ).execute()
            
            return [TextContent(
                type="text",
                text=f"Meeting '{args['title']}' scheduled successfully!\n"
                     f"Event ID: {created_event['id']}\n"
                     f"Start: {start_dt.strftime('%Y-%m-%d %I:%M %p %Z')}\n"
                     f"End: {end_dt.strftime('%Y-%m-%d %I:%M %p %Z')}\n"
                     f"Calendar link: {created_event.get('htmlLink', 'N/A')}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error scheduling meeting: {str(e)}"
            )]

    async def _list_upcoming_events(self, args: dict) -> Sequence[TextContent]:
        try:
            max_results = args.get('max_results', 10)
            days_ahead = args.get('days_ahead', 7)
            
            # Calculate time bounds in local timezone
            now = datetime.now(self.local_timezone)
            time_max = now + timedelta(days=days_ahead)
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return [TextContent(
                    type="text",
                    text=f"No upcoming events found in the next {days_ahead} days."
                )]
            
            event_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                # Convert to local timezone for display
                if 'T' in start:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    start_local = start_dt.astimezone(self.local_timezone)
                    start_display = start_local.strftime('%Y-%m-%d %I:%M %p %Z')
                else:
                    start_display = start
                    
                title = event.get('summary', 'No title')
                location = event.get('location', 'No location')
                event_list.append(f"• {title} - {start_display} ({location})")
            
            return [TextContent(
                type="text",
                text=f"Upcoming events ({len(events)} found):\n" + "\n".join(event_list)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error listing events: {str(e)}"
            )]

    async def _find_free_time(self, args: dict) -> Sequence[TextContent]:
        try:
            date_str = args['date']
            duration_minutes = args['duration_minutes']
            start_hour = args.get('start_hour', 9)
            end_hour = args.get('end_hour', 17)
            
            # Parse the date and create time bounds
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_start = date_obj.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            day_end = date_obj.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            
            # Get events for the day
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=day_start.isoformat() + 'Z',
                timeMax=day_end.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Find free slots
            busy_times = []
            for event in events:
                event_start = datetime.fromisoformat(event['start'].get('dateTime', '').replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(event['end'].get('dateTime', '').replace('Z', '+00:00'))
                busy_times.append((event_start, event_end))
            
            # Sort busy times
            busy_times.sort()
            
            # Find free slots
            free_slots = []
            current_time = day_start
            
            for busy_start, busy_end in busy_times:
                if (busy_start - current_time).total_seconds() >= duration_minutes * 60:
                    free_slots.append((current_time, busy_start))
                current_time = max(current_time, busy_end)
            
            # Check if there's time after the last event
            if (day_end - current_time).total_seconds() >= duration_minutes * 60:
                free_slots.append((current_time, day_end))
            
            if not free_slots:
                return [TextContent(
                    type="text",
                    text=f"No free {duration_minutes}-minute slots available on {date_str} between {start_hour}:00 and {end_hour}:00."
                )]
            
            slot_strings = []
            for start, end in free_slots:
                available_duration = int((end - start).total_seconds() / 60)
                slot_strings.append(f"• {start.strftime('%H:%M')} - {end.strftime('%H:%M')} ({available_duration} minutes available)")
            
            return [TextContent(
                type="text",
                text=f"Free time slots on {date_str} (minimum {duration_minutes} minutes):\n" + "\n".join(slot_strings)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error finding free time: {str(e)}"
            )]

async def main():
    calendar_server = GoogleCalendarServer()
    async with stdio_server() as (read_stream, write_stream):
        await calendar_server.server.run(
            read_stream, write_stream, calendar_server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
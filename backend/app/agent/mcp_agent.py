"""
MCP-based Agent for Project Management Chat
Integrates Gmail and Google Calendar MCP servers to provide agentic capabilities.
"""
from typing import List, Dict, Optional
from contextlib import AsyncExitStack
import json
import logging
from datetime import datetime
import os

from google import genai
from google.genai import types as genai_types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_schema(schema: dict) -> dict:
    """Clean schema by keeping only allowed keys for Gemini function declarations."""
    allowed_keys = {"type", "properties", "required", "description", "title", "default", "enum", "items", "minimum", "maximum"}
    cleaned = {}
    for k, v in schema.items():
        if k in allowed_keys:
            if k == "properties" and isinstance(v, dict):
                # Recursively clean nested properties
                cleaned[k] = {prop_name: clean_schema(prop_val) if isinstance(prop_val, dict) else prop_val 
                             for prop_name, prop_val in v.items()}
            elif k == "items" and isinstance(v, dict):
                # Recursively clean items schema
                cleaned[k] = clean_schema(v)
            else:
                cleaned[k] = v
    return cleaned


class MCPProjectAgent:
    """Agentic assistant for project management with Gmail and Calendar integration."""
    
    def __init__(self):
        self.sessions: List[ClientSession] = []
        self.exit_stack = AsyncExitStack()
        self.gemini_client = genai.Client()
        self.gemini_tools = None
        self.model_name = "gemini-2.0-flash-exp"
        self.available_tools: List[Dict] = []
        self.tool_to_session: Dict[str, ClientSession] = {}
        # Project-specific conversation histories (project_id -> conversation)
        self.project_conversations: Dict[str, List[genai_types.Content]] = {}
        
    async def initialize(self):
        """Initialize MCP server connections."""
        await self._connect_to_servers()
        
    async def _connect_to_server(self, server_name: str, server_config: dict) -> None:
        """Connect to a single MCP server."""
        try:
            # Get the backend directory path
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            
            # Update paths to be absolute
            if "env" in server_config and server_config["env"]:
                for key, value in server_config["env"].items():
                    if value and not os.path.isabs(value):
                        server_config["env"][key] = os.path.join(backend_dir, value)
            
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.sessions.append(session)
            
            # List available tools for this session
            response = await session.list_tools()
            tools = response.tools
            logger.info(f"Connected to {server_name} with tools: {[t.name for t in tools]}")
            
            for tool in tools:
                self.tool_to_session[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}")
            raise
    
    async def _connect_to_servers(self) -> None:
        """Connect to configured MCP servers for project management."""
        # Configuration for Gmail and Google Calendar servers
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        servers = {
            "gmail": {
                "command": "python",
                "args": [os.path.join(backend_dir, "app/mcp_servers/gmail_mcp_server.py")],
                "env": {
                    "GMAIL_CREDENTIALS_FILE": os.path.join(backend_dir, "gmail/google_credentials.json"),
                    "GMAIL_TOKEN_FILE": os.path.join(backend_dir, "gmail/gmail_token.json")
                }
            },
            "google_calendar": {
                "command": "python",
                "args": [os.path.join(backend_dir, "app/mcp_servers/google_calendar_server.py")],
                "env": {
                    "GMAIL_CREDENTIALS_FILE": os.path.join(backend_dir, "gmail/google_credentials.json"),
                    "GMAIL_TOKEN_FILE": os.path.join(backend_dir, "gmail/token.json")
                }
            }
        }
        
        for server_name, server_config in servers.items():
            await self._connect_to_server(server_name, server_config)
    
    async def chat(self, 
                   project_id: str,
                   user_message: str,
                   project_context: str) -> str:
        """
        Process a chat message for a specific project.
        
        Args:
            project_id: Unique identifier for the project
            user_message: User's message
            project_context: Context about the project (title, description, todos, etc.)
            
        Returns:
            AI assistant's response
        """
        # Initialize conversation for this project if not exists
        if project_id not in self.project_conversations:
            # First message includes project context and current date
            today_date = datetime.now().strftime("%Y-%m-%d")
            system_prompt = f"""Today's date is {today_date}. You are a helpful project management assistant with access to Gmail and Google Calendar.

Current Project Context:
{project_context}

You can help the user with:
- Planning and breaking down tasks
- Scheduling meetings and deadlines
- Sending emails to team members or stakeholders
- Finding free time slots for meetings
- Setting priorities and organizing work
- Any other project-related questions

If you need to send emails or schedule meetings, use the available tools. Ask for clarification if needed.

User: {user_message}"""
            
            user_content = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=system_prompt)]
            )
            self.project_conversations[project_id] = [user_content]
        else:
            # Subsequent messages include updated context
            context_update = f"""[Updated Project Context]
{project_context}

User: {user_message}"""
            user_content = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=context_update)]
            )
            self.project_conversations[project_id].append(user_content)
        
        # Prepare MCP tools for Gemini
        if not self.gemini_tools and self.available_tools:
            mcp_tools = self.available_tools
            tools = genai_types.Tool(function_declarations=[
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": clean_schema(tool.get("input_schema", {}))
                }
                for tool in mcp_tools
            ])
            self.gemini_tools = tools
        else:
            tools = self.gemini_tools if self.available_tools else None
        
        # Generate response from Gemini
        config_params = {"temperature": 0.7}
        if tools:
            config_params["tools"] = [tools]
            
        response = await self.gemini_client.aio.models.generate_content(
            model=self.model_name,
            contents=self.project_conversations[project_id],
            config=genai_types.GenerateContentConfig(**config_params)
        )
        
        # Add assistant response to conversation history
        self.project_conversations[project_id].append(response.candidates[0].content)
        
        # Handle function calls (tool invocations)
        turn_count = 0
        max_tool_turns = 10
        
        while response.function_calls and turn_count < max_tool_turns:
            turn_count += 1
            tool_response_parts: List[genai_types.Part] = []
            
            for fc_part in response.function_calls:
                tool_name = fc_part.name
                args = fc_part.args or {}
                logger.info(f"Project {project_id}: Invoking tool '{tool_name}' with args: {args}")
                
                tool_response: dict
                try:
                    session = self.tool_to_session[tool_name]
                    tool_result = await session.call_tool(tool_name, args)
                    logger.info(f"Project {project_id}: Tool '{tool_name}' executed")
                    
                    if tool_result.isError:
                        tool_response = {"error": tool_result.content[0].text}
                        logger.warning(f"Tool '{tool_name}' error: {tool_result.content[0].text}")
                    else:
                        tool_response = {"result": tool_result.content[0].text}
                        logger.info(f"Tool '{tool_name}' result: {tool_result.content[0].text}")
                except Exception as e:
                    tool_response = {"error": f"Tool execution failed: {type(e).__name__}: {e}"}
                    logger.error(f"Tool '{tool_name}' failed: {e}")
                
                tool_response_parts.append(
                    genai_types.Part.from_function_response(
                        name=tool_name,
                        response=tool_response
                    )
                )
            
            # Add tool responses to conversation
            tool_content = genai_types.Content(role="user", parts=tool_response_parts)
            self.project_conversations[project_id].append(tool_content)
            
            logger.info(f"Project {project_id}: Added {len(tool_response_parts)} tool response(s)")
            
            # Get updated response from Gemini
            response = await self.gemini_client.aio.models.generate_content(
                model=self.model_name,
                contents=self.project_conversations[project_id],
                config=genai_types.GenerateContentConfig(**config_params)
            )
            
            # Add new assistant response to history
            self.project_conversations[project_id].append(response.candidates[0].content)
        
        if turn_count >= max_tool_turns and response.function_calls:
            logger.warning(f"Project {project_id}: Stopped after {max_tool_turns} tool calls")
        
        # Extract final text response
        final_text = ""
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    final_text += part.text
        
        return final_text if final_text else "I apologize, but I couldn't generate a response."
    
    async def cleanup(self):
        """Cleanup MCP sessions."""
        await self.exit_stack.aclose()
        self.sessions.clear()
        self.available_tools.clear()
        self.tool_to_session.clear()


# Global agent instance (singleton pattern for efficiency)
_global_agent: Optional[MCPProjectAgent] = None


async def get_mcp_agent() -> MCPProjectAgent:
    """Get or create the global MCP agent instance."""
    global _global_agent
    if _global_agent is None:
        _global_agent = MCPProjectAgent()
        await _global_agent.initialize()
    return _global_agent


async def cleanup_mcp_agent():
    """Cleanup the global MCP agent instance."""
    global _global_agent
    if _global_agent is not None:
        await _global_agent.cleanup()
        _global_agent = None

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
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.sessions: List[ClientSession] = []
        self.calendar_sessions: Dict[str, ClientSession] = {}  # user_id -> calendar session
        self.calendar_exit_stacks: Dict[str, AsyncExitStack] = {}  # user_id -> exit stack for cleanup
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
            
            # Update paths in args to be absolute
            if "args" in server_config and server_config["args"]:
                updated_args = []
                for arg in server_config["args"]:
                    # If arg looks like a path to a Python file, make it absolute
                    if arg.endswith('.py') and not os.path.isabs(arg):
                        updated_args.append(os.path.join(backend_dir, arg))
                    else:
                        updated_args.append(arg)
                server_config["args"] = updated_args
            
            # Update paths in env to be absolute
            # Prepare environment variables
            env = os.environ.copy()
            if "env" in server_config and server_config["env"]:
                # Update paths to be absolute (but not for non-path env vars like CALENDAR_USER_ID)
                for key, value in server_config["env"].items():
                    if value and isinstance(value, str) and not os.path.isabs(value):
                        # Only convert to absolute path if it looks like a file path
                        if key.endswith("_FILE") or key.endswith("_PATH") or "/" in value or "\\" in value:
                            server_config["env"][key] = os.path.join(backend_dir, value)
                    env[key] = server_config["env"][key]
            
            server_params = StdioServerParameters(
                command=server_config["command"],
                args=server_config["args"],
                env=env if "env" in server_config else None
            )
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
    
    async def _get_calendar_session_for_user(self, user_id: str) -> ClientSession:
        """Get or create a calendar server session for a specific user."""
        if user_id in self.calendar_sessions:
            return self.calendar_sessions[user_id]
        
        # Create a new calendar server subprocess for this user
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Use environment variable to pass user_id to the server
        server_config = {
            "command": "python",
            "args": [os.path.join(backend_dir, "mcp_servers/google_calendar_server.py")],
            "env": {
                "CALENDAR_USER_ID": user_id,  # Pass user_id via env
                "PYTHONPATH": backend_dir
            }
        }
        
        # Create new exit stack for this user's server
        user_exit_stack = AsyncExitStack()
        await user_exit_stack.__aenter__()
        
        try:
            # Prepare environment variables
            env = os.environ.copy()
            if "env" in server_config:
                env.update(server_config["env"])
            
            server_params = StdioServerParameters(
                command=server_config["command"],
                args=server_config["args"],
                env=env
            )
            stdio_transport = await user_exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await user_exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            
            # Store session and exit stack for cleanup
            self.calendar_sessions[user_id] = session
            self.calendar_exit_stacks[user_id] = user_exit_stack
            
            # Register tools from this session
            response = await session.list_tools()
            tools = response.tools
            logger.info(f"Connected calendar server for user {user_id} with tools: {[t.name for t in tools]}")
            
            for tool in tools:
                # Map tool name to this user's session
                self.tool_to_session[tool.name] = session
                # Only add tools once to available_tools (they're the same for all users)
                if not any(t["name"] == tool.name for t in self.available_tools):
                    self.available_tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    })
            
            return session
        except Exception as e:
            # Cleanup on error
            await user_exit_stack.aclose()
            raise
    
    async def _connect_to_servers(self) -> None:
        """Connect to configured MCP servers for project management."""
        # Configuration for non-user-specific servers
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config_path = os.path.join(backend_dir, "server_config.json")
        
        # Load server configuration from server_config.json
        try:
            with open(config_path, 'r') as f:
                # Remove comments from JSON (simple approach)
                content = f.read()
                lines = [line.split('//')[0] for line in content.split('\n')]
                clean_content = '\n'.join(lines)
                config = json.loads(clean_content)
                servers = config.get("mcpServers", {})
                servers["google_calendar"]["env"]["CALENDAR_USER_ID"] = self.user_id
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}, using default servers")
            # Fallback to hardcoded configuration
            servers = {
                "gmail": {
                    "command": "python",
                    "args": [os.path.join(backend_dir, "mcp_servers/gmail_mcp_server.py")],
                    "env": {
                        "GMAIL_CREDENTIALS_FILE": os.path.join(backend_dir, "gmail/google_credentials.json"),
                        "GMAIL_TOKEN_FILE": os.path.join(backend_dir, "gmail/gmail_token.json")
                    }
                },
                "google_calendar": {
                    "command": "python",
                    "args": [os.path.join(backend_dir, "mcp_servers/google_calendar_server.py")],
                    "env": {
                        "CALENDAR_USER_ID": self.user_id,
                    }
                }
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse server_config.json: {e}")
            raise
        
        # Only connect to servers we need for project management
        # Filter to gmail, google_calendar, and project_plan
        enabled_servers = ["gmail", "google_calendar", "project_plan"]
        
        for server_name in enabled_servers:
            if server_name in servers:
                await self._connect_to_server(server_name, servers[server_name])
            else:
                logger.warning(f"Server '{server_name}' not found in configuration")
        # Connect to calendar server for this agent's user
        await self._get_calendar_session_for_user(self.user_id)
    async def chat(self, 
                   project_id: str,
                   user_message: str,
                   project_context: str) -> tuple[str, Optional[str]]:
        """
        Process a chat message for a specific project.
        
        Args:
            project_id: Unique identifier for the project
            user_message: User's message
            project_context: Context about the project (title, description, todos, etc.)
            
        Returns:
            tuple: (AI assistant's response, updated plan or None)
        """
        # Track if plan was updated
        updated_plan: Optional[str] = None
        
        # Initialize conversation for this project if not exists
        if project_id not in self.project_conversations:
            # First message includes project context and current date
            today_date = datetime.now().strftime("%Y-%m-%d")
            system_prompt = f"""Today's date is {today_date}. You are a helpful project management assistant with access to Gmail, Google Calendar, and Project Plan Management tools.

**CURRENT PROJECT ID: {project_id}**

Current Project Context:
{project_context}

You can help the user with:
- **Creating and managing execution plans**: Use the update_execution_plan tool to create comprehensive project plans
- **Refining plans**: When users ask to modify or improve the plan, use update_execution_plan with action='refine'
- **Planning and breaking down tasks**: Help structure work into manageable pieces
- **Scheduling meetings and deadlines**: Use calendar tools to find time and schedule events
- **Sending emails**: Communicate with team members or stakeholders via Gmail
- **Finding free time slots**: Check calendar availability
- **Setting priorities**: Help organize and prioritize work
- Any other project-related questions

**CRITICAL INSTRUCTIONS:**
1. When the user asks you to generate, create, update, or refine an execution plan, you MUST use the 'update_execution_plan' tool. Don't just describe the plan in your response - actually call the tool to save it!
2. ALWAYS use the project_id "{project_id}" when calling project plan management tools (update_execution_plan, get_execution_plan, append_to_plan, clear_execution_plan).
3. You have ALL the information about the current project in the context above - you should NEVER ask the user for the project ID.
4. When working with the current project's plan, automatically use the project_id shown above.

If you need to send emails or schedule meetings, use the available tools. Ask for clarification only when you need information that's not in the project context.

User: {user_message}"""
            
            user_content = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=system_prompt)]
            )
            self.project_conversations[project_id] = [user_content]
        else:
            # Subsequent messages include updated context
            context_update = f"""[Updated Project Context - Project ID: {project_id}]
{project_context}

Remember: Always use project_id "{project_id}" for any project plan management tool calls.

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
                    # For calendar tools, ensure we use the correct user's session
                    if tool_name in ["schedule_meeting", "list_upcoming_events", "find_free_time"]:
                        # Get or create calendar session for this agent's user
                        session = await self._get_calendar_session_for_user(self.user_id)
                    else:
                        session = self.tool_to_session.get(tool_name)
                        if not session:
                            raise ValueError(f"No session found for tool '{tool_name}'")
                    
                    tool_result = await session.call_tool(tool_name, args)
                    logger.info(f"Project {project_id}: Tool '{tool_name}' executed")
                    
                    # Track plan updates
                    if tool_name == "update_execution_plan" and not tool_result.isError:
                        # Extract the plan content from the args and update outer scope variable
                        updated_plan = args.get("plan_content", "")
                        logger.info(f"Project {project_id}: Plan updated via MCP tool with content length: {len(updated_plan)}")
                    
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
        
        response_text = final_text if final_text else "I apologize, but I couldn't generate a response."
        return response_text, updated_plan
    
    async def cleanup(self):
        """Cleanup MCP sessions."""
        # Cleanup calendar sessions
        for user_id, exit_stack in self.calendar_exit_stacks.items():
            try:
                await exit_stack.aclose()
            except Exception as e:
                logger.error(f"Error cleaning up calendar session for user {user_id}: {e}")
        
        # Cleanup other sessions
        await self.exit_stack.aclose()
        self.sessions.clear()
        self.calendar_sessions.clear()
        self.calendar_exit_stacks.clear()
        self.available_tools.clear()
        self.tool_to_session.clear()


# Per-user agent instances (one per user for proper isolation)
_user_agents: Dict[str, MCPProjectAgent] = {}


async def get_mcp_agent(user_id: str) -> MCPProjectAgent:
    """Get or create an MCP agent instance for a specific user."""
    global _user_agents
    if user_id not in _user_agents:
        agent = MCPProjectAgent(user_id)
        await agent.initialize()
        _user_agents[user_id] = agent
    return _user_agents[user_id]


async def cleanup_mcp_agent(user_id: Optional[str] = None):
    """Cleanup MCP agent instance(s)."""
    global _user_agents
    if user_id:
        if user_id in _user_agents:
            await _user_agents[user_id].cleanup()
            del _user_agents[user_id]
    else:
        # Cleanup all
        for agent in _user_agents.values():
            await agent.cleanup()
        _user_agents.clear()

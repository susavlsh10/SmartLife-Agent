"""
MCP Server for Project Plan Management
Provides tools for the AI agent to manage project execution plans
"""

import asyncio
import logging
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('project-plan-server')

# In-memory storage for plans (will be persisted via the main app's database)
# This is just a temporary cache for the MCP server session
plans_cache: dict[str, str] = {}

# Create server instance
mcp = Server("project-plan-server")


@mcp.list_tools()
async def list_tools() -> list[Tool]:
    """List available plan management tools."""
    return [
        Tool(
            name="update_execution_plan",
            description="""Update or create the execution plan for a project.
            
Use this tool when you need to:
- Create a new execution plan from scratch
- Update an existing plan with modifications
- Refine the plan based on user feedback
- Add or remove sections from the plan

The plan should be comprehensive and include:
- Clear phases or milestones
- Specific tasks with timelines
- Dependencies between tasks
- Key deliverables
- Risk mitigation strategies

Format the plan in clear, structured markdown.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The unique identifier for the project"
                    },
                    "plan_content": {
                        "type": "string",
                        "description": "The complete execution plan in markdown format"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "refine"],
                        "description": "The type of action: create (new plan), update (replace existing), or refine (modify existing)"
                    }
                },
                "required": ["project_id", "plan_content", "action"]
            }
        ),
        Tool(
            name="get_execution_plan",
            description="""Retrieve the current execution plan for a project.
            
Use this tool when you need to:
- Check if a plan already exists
- Review the current plan before making updates
- Reference the existing plan structure""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The unique identifier for the project"
                    }
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="append_to_plan",
            description="""Append a new section to the existing execution plan.
            
Use this tool when you need to:
- Add a new phase or milestone
- Include additional considerations
- Add risk factors or mitigation strategies
- Extend the plan without replacing everything""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The unique identifier for the project"
                    },
                    "section_title": {
                        "type": "string",
                        "description": "Title of the section to append"
                    },
                    "section_content": {
                        "type": "string",
                        "description": "Content to append in markdown format"
                    }
                },
                "required": ["project_id", "section_title", "section_content"]
            }
        ),
        Tool(
            name="clear_execution_plan",
            description="""Clear/delete the execution plan for a project.
            
Use this tool when you need to:
- Remove an outdated plan before creating a new one
- Start fresh with plan generation""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The unique identifier for the project"
                    }
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="generate_todos_from_plan",
            description="""Generate a list of TODO items from the execution plan.
            
Use this tool when you need to:
- Break down an execution plan into actionable tasks
- Create a TODO list from project phases and milestones
- Extract specific tasks with due dates from the plan

The tool will analyze the execution plan and create structured TODO items with:
- Clear task descriptions
- Appropriate due dates based on the timeline
- Logical ordering

Return the tasks as a JSON array with this structure:
[
  {
    "text": "Task description",
    "due_date": "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS" (optional)
  }
]""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The unique identifier for the project"
                    },
                    "todos": {
                        "type": "array",
                        "description": "Array of TODO items to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "The task description"
                                },
                                "due_date": {
                                    "type": "string",
                                    "description": "Optional due date in YYYY-MM-DD or ISO format"
                                }
                            },
                            "required": ["text"]
                        }
                    }
                },
                "required": ["project_id", "todos"]
            }
        )
    ]


@mcp.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls for plan management."""
    
    if name == "update_execution_plan":
        project_id = arguments["project_id"]
        plan_content = arguments["plan_content"]
        action = arguments["action"]
        
        logger.info(f"Updating execution plan for project {project_id} (action: {action})")
        
        # Store in cache
        plans_cache[project_id] = plan_content
        
        action_text = {
            "create": "created",
            "update": "updated",
            "refine": "refined"
        }.get(action, "updated")
        
        return [
            TextContent(
                type="text",
                text=f"Successfully {action_text} execution plan for project {project_id}. "
                     f"The plan has been saved and will be visible to the user."
            )
        ]
    
    elif name == "get_execution_plan":
        project_id = arguments["project_id"]
        
        logger.info(f"Retrieving execution plan for project {project_id}")
        
        plan = plans_cache.get(project_id)
        
        if plan:
            return [
                TextContent(
                    type="text",
                    text=f"Current execution plan:\n\n{plan}"
                )
            ]
        else:
            return [
                TextContent(
                    type="text",
                    text="No execution plan exists for this project yet."
                )
            ]
    
    elif name == "append_to_plan":
        project_id = arguments["project_id"]
        section_title = arguments["section_title"]
        section_content = arguments["section_content"]
        
        logger.info(f"Appending to execution plan for project {project_id}")
        
        current_plan = plans_cache.get(project_id, "")
        
        # Append the new section
        updated_plan = current_plan + f"\n\n## {section_title}\n\n{section_content}"
        plans_cache[project_id] = updated_plan
        
        return [
            TextContent(
                type="text",
                text=f"Successfully appended '{section_title}' section to the execution plan."
            )
        ]
    
    elif name == "clear_execution_plan":
        project_id = arguments["project_id"]
        
        logger.info(f"Clearing execution plan for project {project_id}")
        
        if project_id in plans_cache:
            del plans_cache[project_id]
        
        return [
            TextContent(
                type="text",
                text=f"Successfully cleared execution plan for project {project_id}."
            )
        ]
    
    elif name == "generate_todos_from_plan":
        project_id = arguments["project_id"]
        todos = arguments["todos"]
        
        logger.info(f"Generating {len(todos)} TODO items for project {project_id}")
        
        # Return the todos as JSON for the backend to process
        import json
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "todos": todos,
                    "count": len(todos)
                })
            )
        ]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server."""
    logger.info("Starting Project Plan MCP Server")
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(
            read_stream,
            write_stream,
            mcp.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

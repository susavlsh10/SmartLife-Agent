#!/usr/bin/env python3
"""
Test script to verify MCP server connections
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.agent.mcp_agent import MCPProjectAgent


async def main():
    """Test MCP server connections."""
    print("=== Testing MCP Server Connections ===\n")
    
    agent = MCPProjectAgent()
    
    try:
        print("Initializing agent and connecting to MCP servers...")
        await agent.initialize()
        
        print(f"\n✓ Successfully connected to {len(agent.sessions)} MCP server(s)")
        print(f"✓ Total tools available: {len(agent.available_tools)}")
        
        print("\n=== Available Tools ===")
        for tool in agent.available_tools:
            print(f"  • {tool['name']}: {tool['description'][:80]}...")
        
        # Check specifically for project_plan tools
        project_plan_tools = [t for t in agent.available_tools if 'plan' in t['name'].lower()]
        
        if project_plan_tools:
            print(f"\n✓ SUCCESS: Found {len(project_plan_tools)} project plan tool(s):")
            for tool in project_plan_tools:
                print(f"  • {tool['name']}")
        else:
            print("\n✗ WARNING: No project plan tools found!")
            print("  The project_plan MCP server may not be loading correctly.")
        
        print("\n=== Tool to Session Mapping ===")
        for tool_name, session in agent.tool_to_session.items():
            print(f"  • {tool_name} -> {session}")
        
    except Exception as e:
        print(f"\n✗ ERROR: Failed to initialize agent: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        await agent.exit_stack.aclose()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

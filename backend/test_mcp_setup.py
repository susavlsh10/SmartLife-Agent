#!/usr/bin/env python3
"""
Test script to verify MCP agent setup
Run with: uv run python test_mcp_setup.py
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_mcp_agent():
    """Test MCP agent initialization"""
    print("🧪 Testing MCP Agent Setup\n")
    
    try:
        print("1️⃣ Importing MCP agent module...")
        from app.agent.mcp_agent import MCPProjectAgent, get_mcp_agent
        print("   ✅ Import successful\n")
        
        print("2️⃣ Creating MCP agent instance...")
        agent = MCPProjectAgent()
        print("   ✅ Agent created\n")
        
        print("3️⃣ Initializing MCP servers...")
        print("   ⏳ Connecting to Gmail and Calendar servers...")
        print("   (This may take a few seconds...)")
        
        try:
            await agent.initialize()
            print(f"   ✅ Connected successfully!")
            print(f"   📊 Available tools: {len(agent.available_tools)}")
            
            if agent.available_tools:
                print("\n   🔧 Available MCP Tools:")
                for tool in agent.available_tools:
                    print(f"      • {tool['name']}: {tool['description']}")
            else:
                print("   ⚠️  No tools available (OAuth may not be configured)")
                
        except Exception as e:
            print(f"   ⚠️  Server connection failed: {e}")
            print("\n   This is expected if Gmail OAuth is not set up yet.")
            print("   The app will work, but Gmail/Calendar features won't be available.")
            
        print("\n4️⃣ Testing chat capability...")
        test_context = """Project: Test Project
Description: Testing MCP integration
Due Date: 2025-11-15

Todo Items:
1. [○] Set up OAuth
2. [○] Test email sending
"""
        
        try:
            response = await agent.chat(
                project_id="test-project",
                user_message="What can you help me with?",
                project_context=test_context
            )
            print(f"   ✅ Chat response received!")
            print(f"\n   🤖 AI Response:\n   {response[:200]}...")
            
        except Exception as e:
            print(f"   ⚠️  Chat test failed: {e}")
            
        print("\n5️⃣ Cleaning up...")
        await agent.cleanup()
        print("   ✅ Cleanup complete")
        
        print("\n" + "="*60)
        print("✅ MCP Agent Setup Test Complete!")
        print("="*60)
        
        if agent.available_tools:
            print("\n🎉 Your MCP integration is fully functional!")
            print("   You can now use Gmail and Calendar features in project chat.")
        else:
            print("\n📝 Next steps:")
            print("   1. Set up Google OAuth credentials (see MCP_SETUP.md)")
            print("   2. Save credentials to backend/gmail/google_credentials.json")
            print("   3. Run this test again to verify")
            
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        print("\n   Please run: uv sync")
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SmartLife Agent - MCP Setup Test")
    print("="*60 + "\n")
    
    # Check for environment variables
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not found in environment")
        print("   Set it in .env file or export it")
        print()
    
    asyncio.run(test_mcp_agent())

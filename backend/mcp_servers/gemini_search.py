from fastmcp import FastMCP
from google import genai
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("gemini_search")

SYSTEM_PROMPT = "You are a lightweight AI agent designed to perform accurate web searches and retrieve relevant information. Use the Google Search tool to find up-to-date and reliable content. Summarize your findings into concise, factual, and self-contained answers. Your output will be consumed by a downstream Gemini model that will generate the final user response, so prioritize brevity, precision, and relevance."
client = genai.Client()

grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

config = types.GenerateContentConfig(
    tools=[grounding_tool],
    system_instruction=SYSTEM_PROMPT,
    temperature=0,
    thinking_config=types.ThinkingConfig(thinking_budget=0), # thinking
)

@mcp.tool()
def gemini_retrieval_generation(query: str) -> str:
    """
    Perform a web search and generation using Gemini's Google Search grounding.
    
    Args:
        query: The search query or question to answer
    
    Returns:
        The response from Gemini with web search grounding
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
            config=config,
        )
        return response.text
    except Exception as e:
        return f"Error performing web search: {str(e)}"
    
if __name__ == "__main__":
    mcp.run(transport='stdio')
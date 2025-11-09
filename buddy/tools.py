"""
Tools for Buddy voice agent.
"""

import asyncio
import logging
import os
from typing import Optional

import httpx
from livekit.agents import function_tool, RunContext, ToolError

logger = logging.getLogger("tools")


@function_tool()
async def find_nearby_events(
    context: RunContext,
    search_query: str,
) -> str:
    """Search for local events in San Francisco based on user's request.
    
    Use this when the user asks about events, what's happening, concerts, festivals, 
    things to do tonight/this week, etc.
    
    Args:
        search_query: Concise search query (e.g. "live music SF this weekend", 
                     "food festivals San Francisco November 2025")
    """
    logger.info(f"🔍 Buddy searching for events: {search_query}")
    
    # Provide feedback for longer searches
    async def _speak_status():
        await asyncio.sleep(0.5)
        await context.session.generate_reply(
            instructions="You're searching for events but it's taking a moment. "
                        "Tell the user you're sniffing around for the best options - be playful and brief."
        )
    
    status_task = asyncio.create_task(_speak_status())
    
    try:
        # Call Linkup API
        api_key = os.getenv("LINKUP_API_KEY")
        if not api_key:
            raise ToolError("Event search is temporarily unavailable - missing API key")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.linkup.so/v1/search",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "q": search_query,
                    "depth": "standard",
                    "outputType": "searchResults"
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Cancel status update since we got results
            status_task.cancel()
            
            # Log raw API response
            logger.info(f"📦 Linkup API response keys: {list(data.keys())}")
            logger.info(f"📦 Number of results: {len(data.get('results', []))}")
            
            # Parse results
            if not data.get("results"):
                logger.warning("❌ No results found in API response")
                return "I couldn't find any events matching that search. Want to try something different?"
            
            # Format results for Buddy to present naturally
            results_text = []
            for i, result in enumerate(data["results"][:5], 1):
                title = result.get("name", "Event")
                url = result.get("url", "")
                snippet = result.get("content", "")[:200]
                
                # Log each result for verification
                logger.info(f"  Result {i}: {title}")
                logger.info(f"    URL: {url}")
                logger.info(f"    Snippet: {snippet[:100]}...")
                
                results_text.append(f"{i}. {title}\n{snippet}\n{url}")
            
            formatted = "\n\n".join(results_text)
            
            # Log the full tool return value that LLM will receive
            tool_response = f"Here are some events I found:\n\n{formatted}\n\n" \
                          f"Present these naturally and enthusiastically. Mention the most exciting ones first!"
            
            logger.info(f"✅ Tool returning to LLM ({len(tool_response)} chars)")
            logger.info(f"📝 Tool response preview:\n{tool_response[:500]}...")
            
            return tool_response
    
    except httpx.HTTPError as e:
        logger.error(f"❌ Linkup API HTTP error: {e}")
        logger.error(f"   Status code: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
        logger.error(f"   Response body: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        status_task.cancel()
        raise ToolError("Having trouble finding events right now - can you try again in a moment?")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in find_nearby_events: {e}", exc_info=True)
        status_task.cancel()
        raise ToolError("Oops, something went wrong finding events. Can you rephrase what you're looking for?")
"""
Tool-calling agent loop for Field Companion.
Gemma is the orchestrator, not the classifier.
Max 4 tool-calling iterations per query.
"""

import json
import logging
from typing import Optional

from app.llm import chat
from app.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 4

# ---------------------------------------------------------------------------
# System prompt — the core of the agent's behaviour
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Field Companion, a concise nature guide for outdoor walks.

RULES (follow every one):

1. GROUNDING: Every species you mention MUST come from a tool result (species_lookup or checklist_check). Never invent or guess a species name. If no tool result supports a claim, say "I'm not sure" and suggest what to observe or record again.

2. TOOLS FIRST: When the user describes an animal, bird, plant, or sighting (colors, size, marks):
   - Formulate 1 to 3 specific candidate species names that fit the description (e.g., for a small black bird with white wing patch, think of candidate species like "Oriental Magpie-Robin" or "Magpie-Robin").
   - DO NOT pass literal descriptive phrases (like "small black bird" or "white patch") to `species_lookup`. Always pass candidate species names!
   - Call `species_lookup` for each candidate name to verify if it is in the regional checklist.
   - If confirmed by the checklist, name the species, state why, and provide what to look for.
   - Only mention species that are verified in the checklist. Do not invent any unverified species.

3. CONFIDENCE: If the candidate or identification is uncertain, say so clearly. Use phrases like "this could be" or "most likely" with a suggestion of what feature to look at to confirm.

4. CONCISENESS: Keep spoken replies under 25 words. The full text appears on screen, so the voice output should be brief. No exclamation marks, no emojis.

5. LOOK BACK AT NATURE: Always end with ONE specific thing the user should look at or listen for in the real world to confirm the identification. Examples: "Check if the tail feathers have white edges", "Look at the leaf shape — are the edges serrated?"

6. SAFETY (CRITICAL): For plants and fungi, NEVER say anything is safe to eat, touch, taste, or use medicinally. Always include this disclaimer: "Do not eat or touch any plant or fungus based on this identification."

7. REGIONAL AWARENESS: If a species is not expected in the user's region (checklist_check returns in_region=false), flag this clearly: "This species is not typically found here — the identification may be wrong."

8. JOURNAL: When the user confirms a sighting or wants to save it, use journal_add. When they ask about past sightings, use journal_search.

9. TOOL OUTPUT ONLY: Your answer must be based ONLY on what the tools return. Do not add species information from your training data. If a tool says "not found", say so.

10. FORMAT: Lead with the most likely species name. Then a brief reason. Then what to look for. Keep it structured but natural.
"""


def run_agent(
    user_message: str,
    conversation_history: list[dict] = None,
    system_prompt: str = None,
    extra_context: str = None,
    image_base64: str = None,
) -> dict:
    """
    Run the agent loop with tool calling.

    Args:
        user_message: The user's question or description
        conversation_history: Previous messages in the conversation
        system_prompt: Override the default system prompt
        extra_context: Additional context (e.g., classifier results, location)
        image_base64: Optional base64-encoded image for multimodal queries

    Returns:
        dict with:
            - response: The agent's final text response
            - tools_used: List of tool names that were called
            - iterations: Number of loop iterations used
            - tool_results: Raw tool results for debugging
    """
    prompt = system_prompt or SYSTEM_PROMPT
    messages = [{"role": "system", "content": prompt}]

    # Add conversation history
    if conversation_history:
        messages.extend(conversation_history)

    # Build the user message with any extra context
    content = user_message
    if extra_context:
        content = f"{user_message}\n\n[Context from classifiers]\n{extra_context}"

    if image_base64:
        user_payload = [
            {"type": "text", "text": content},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
            },
        ]
    else:
        user_payload = content

    messages.append({"role": "user", "content": user_payload})

    tools_used = []
    tool_results = []
    iterations = 0

    for i in range(MAX_ITERATIONS):
        iterations = i + 1
        logger.info(f"Agent iteration {iterations}/{MAX_ITERATIONS}")

        try:
            response = chat(
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                max_tokens=512,
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {
                "response": "Something went wrong with the model. Please try again.",
                "tools_used": tools_used,
                "iterations": iterations,
                "tool_results": tool_results,
                "error": str(e),
            }

        choice = response.choices[0]
        message = choice.message

        # If the model wants to call tools
        if message.tool_calls:
            # Add the assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            # Execute each tool call
            for tc in message.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info(f"Calling tool: {tool_name}({tool_args})")
                result = execute_tool(tool_name, tool_args)
                tools_used.append(tool_name)
                tool_results.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": json.loads(result),
                })

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # Continue the loop — let the model process tool results
            continue

        # No tool calls — the model has a final answer
        final_response = message.content or ""

        return {
            "response": final_response,
            "tools_used": tools_used,
            "iterations": iterations,
            "tool_results": tool_results,
        }

    # If we exhausted all iterations
    logger.warning("Agent hit max iterations")
    return {
        "response": "I was not able to complete the analysis. Try describing what you see in more detail.",
        "tools_used": tools_used,
        "iterations": iterations,
        "tool_results": tool_results,
    }


def run_photo_agent(
    image_base64: str,
    user_message: str = "What species is in this photo?",
    checklist_context: str = None,
) -> dict:
    """
    Run the agent for photo identification.
    The image is sent to Gemma vision along with checklist context.
    """
    photo_prompt = SYSTEM_PROMPT + """

PHOTO IDENTIFICATION RULES:
- You are looking at a photo the user took in the field.
- Identify candidate species visible in the image.
- Call `species_lookup` for each candidate name to verify against the local checklist.
- Formulate the top candidates, each with what visual feature supports it.
- Always provide one key feature to look at to confirm or rule it out.
- For plants and fungi, apply the safety rule: never state it is safe to touch or eat.
"""
    if checklist_context:
        photo_prompt += f"\n\nLocal checklist context:\n{checklist_context}"

    return run_agent(
        user_message=user_message,
        system_prompt=photo_prompt,
        image_base64=image_base64,
    )

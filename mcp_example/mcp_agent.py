"""Example Agent which uses MCP to call additional tools."""

import json
import os

from openai import AsyncAzureOpenAI
from openai.types.chat.chat_completion import ChatCompletion

from .mcp_client import MCPClient

MODEL_NAME = "gpt4o-mini"
SYSTEM_PROMPT = """Du bist ein hilfreicher Assistent, der hilft, Informationen zu beschaffen.
Dazu stehen dir einige Tools / Funktionen zur Verfügung, die du nutzen sollst.
Wenn es Sinn macht und du dir sicher bist, rufe diese Funktionen auf, um Informationen zu sammeln und deine Antwort zu vervollständigen.
Wenn du dir unsicher bist, ob du eine Funktion aufrufen sollst, dann frage den Nutzer, ob er das möchte.
Nutze die Antworten aus diesen Funktionsaufrufen, um präzise und informative Antworten zu liefern.
Weise den Nutzer auf die verfügbaren Tools und deren Fähigkeiten hin.
Nutze stets die Tools, um bei Bedarf auf Echtzeitinformationen zuzugreifen.

Engagiere dich auf freundliche Weise, um das Chat-Erlebnis zu verbessern.

# Tools

{tools}

# Hinweise

- Stelle sicher, dass die Antworten auf den neuesten Informationen aus den Funktionsaufrufen basieren.
- Bewahre während des gesamten Dialogs einen ansprechenden, unterstützenden und freundlichen Ton.
- Hebe stets die Möglichkeiten der verfügbaren Tools hervor, um den Nutzer umfassend zu unterstützen.
- Die Tools sind speziell für die Informationsbeschaffung ausgelegt."""

CLIENT = AsyncAzureOpenAI(
    azure_endpoint=os.environ.get("OPENAI_AZURE_ENDPOINT"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    api_version="2024-06-01",
)

LOG_FUNCTION_CALLING = True


async def chat_loop(query: str, tools: dict, messages: list[dict]) -> tuple[str, list]:
    """Main interaction loop which processes user queries using the LLM and available tools.

    This function:
    1. Sends the user query to the LLM with context about available tools
    2. Processes the LLM's response, including any tool calls
    3. Returns the final response to the user

    Args:
        query: User's input question or command
        tools: Dictionary of available database tools and their schemas
        messages: list of messages to pass to the LLM, defaults to None

    """
    # add user query to the messages list
    messages.append({"role": "user", "content": query})
    # Query LLM with the system prompt, user query, and available tools
    first_response = await CLIENT.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=([t["schema"] for t in tools.values()] if len(tools) > 0 else None),
    )
    # detect how the LLM call was completed:
    # tool_calls: if the LLM used a tool
    # stop: If the LLM generated a general response
    if first_response.choices[0].message.tool_calls is not None:
        # Extract tool use details from response
        messages = await append_tool_call(first_response, messages)

        # Query LLM with the user query and the tool results
        new_response = await CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
        )
    # stop: If the LLM generated a general response
    elif first_response.choices[0].finish_reason == "stop":
        # If the LLM stopped on its own, use the first response
        new_response = first_response

    else:
        msg = f"Unknown stop reason: {first_response.choices[0].finish_reason}"
        raise ValueError(msg)

    # Add the LLM response to the messages list
    messages.append(
        {"role": "assistant", "content": new_response.choices[0].message.content},
    )

    # Return the LLM response and messages
    return new_response.choices[0].message.content, messages


async def append_tool_call(first_response: ChatCompletion, messages: list) -> list:
    """Call the tool with the arguments and append the result to the messages list."""
    for tool_call in first_response.choices[0].message.tool_calls:
        arguments = (
            json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
        )
        messages.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": json.dumps(arguments),
                        },
                    },
                ],
            },
        )
        # Call the tool with the arguments using our callable initialized in the tools dict
        async with MCPClient() as mcp_client:
            tool_callable = mcp_client.call_tool(tool_call.function.name)
            tool_result = await tool_callable(**arguments)
        if LOG_FUNCTION_CALLING:
            print("------------------------------------------")
            print(f"Calling Function: {tool_call.function.name} with args: {arguments}")
            print(f"Function Result: {tool_result}")
            print("------------------------------------------")

        # Add the tool result to the messages list
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": json.dumps(tool_result),
            },
        )
    return messages


async def prep_messages_with_system_prompt(tools_dict: dict) -> list:
    """Prepare the initial system prompt with available tools."""
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                tools="\n- ".join(
                    [f"{t['name']}: {t['schema']['function']['description']}" for t in tools_dict.values()],
                ),
            ),
        },
    ]


async def get_available_tools() -> dict:
    """Get available tools from the MCP server."""
    async with MCPClient() as mcp_client:
        tools = await mcp_client.get_available_tools()
    return {
        tool.name: {
            "name": tool.name,
            "schema": {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            },
        }
        for tool in tools
    }


async def main() -> None:
    """Main function that sets up the MCP server, initializes tools, and runs the interactive loop."""
    # Start MCP client and create interactive session
    tools = await get_available_tools()
    messages = await prep_messages_with_system_prompt(tools)

    while True:
        try:
            # Get user input and check for exit commands
            user_input = input("\nEnter your prompt (or 'quit' to exit): ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break

            # Process the prompt and run chat loop
            response, messages = await chat_loop(user_input, tools, messages)
            print("\nResponse:", response)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:  # noqa: BLE001
            print(f"\nError occurred: {e}")

# Model Context Protocol

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is a standardized way to provides tools to an LLM.

## Application

This demo showcases a simple agent application (in german language) that uses the Model Context Protocol to provide tools to an LLM.

The tools are provided through a server which can be found at `mcp_example/mcp_server.py`.
These contain a web search, a wikipedia search and a function for the current daytime.

The MCP client is located at `mcp_example/mcp_client.py` and can connect to the server.

The agent, which uses the MCPClient to connect to the MCP server is located at `mcp_example/mcp_agent.py`.
It contains a german agent, which answers questions in german language using OpenAI GPT-4o-mini.

## Requirements

Install the requirements:

```bash
#poetry
poetry install

#or with pip
pip install -e .
```

The MCP server needs to be started before the agent can be used. The server can be started with the following command:

```bash
python mcp_example/mcp_server.py
```

The agent uses the OpenAI API, for which the endpoint and api key need to be set as environment variables.

```bash
OPENAI_ENDPOINT=<your_openai_endpoint>
OPENAI_API_KEY=<your_openai_api_key>
```

Afterwards, the agent can be started with the following command:

```bash
python -m mcp_example
```

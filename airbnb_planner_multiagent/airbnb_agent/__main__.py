# ruff: noqa: E501, G201, G202
# pylint: disable=logging-fstring-interpolation

import asyncio
import os
import sys

from contextlib import asynccontextmanager
from typing import Any

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent_executor import AirbnbAgentExecutor
from airbnb_agent import AirbnbAgent
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient


load_dotenv(override=True)

SERVER_CONFIGS = {
    "bnb": {
        "command": "npx",
        "args": ["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"],
        "transport": "stdio",
    },
}

app_context: dict[str, Any] = {}


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = int(os.environ.get("PORT", 8080))
DEFAULT_LOG_LEVEL = "info"

@asynccontextmanager
async def app_lifespan(context: dict[str, Any]):
    """Manages the lifecycle of shared resources like the MCP client and tools."""
    print("Lifespan: Initializing MCP client and tools...")
    try:
        client = MultiServerMCPClient(SERVER_CONFIGS)
        context["mcp_client"] = client
        context["mcp_tools"] = await client.get_tools()
        tool_count = len(context["mcp_tools"]) if context["mcp_tools"] else 0
        print(f"Lifespan: MCP Tools preloaded successfully ({tool_count} tools found).")
        yield
    except Exception as e:
        print(f"Lifespan: Error during initialization: {e}", file=sys.stderr)
        raise
    finally:
        print("Lifespan: Shutting down MCP client...")
        if "mcp_client" in context:
            # No explicit close method is documented, so we'll just clear the context
            pass
        print("Lifespan: Clearing application context.")
        context.clear()

def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, log_level: str = DEFAULT_LOG_LEVEL):
    """Command Line Interface to start the Airbnb Agent server."""
    # Verify an API key is set.
    # Not required if using Vertex AI APIs.
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI") != "TRUE" and not os.getenv(
        "GOOGLE_API_KEY"
    ):
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set and "
            "GOOGLE_GENAI_USE_VERTEXAI is not TRUE."
        )

    async def run_server_async():
        async with app_lifespan(app_context):
            # Initialize AirbnbAgentExecutor with preloaded tools
            airbnb_agent_executor = AirbnbAgentExecutor(
                mcp_tools=app_context.get("mcp_tools", [])
            )

            request_handler = DefaultRequestHandler(
                agent_executor=airbnb_agent_executor,
                task_store=InMemoryTaskStore(),
            )

            # Create the A2AServer instance
            a2a_server = A2AStarletteApplication(
                agent_card=get_agent_card(host, port), http_handler=request_handler
            )

            # Get the ASGI app from the A2AServer instance
            asgi_app = a2a_server.build()

            config = uvicorn.Config(
                app=asgi_app,
                host=host,
                port=port,
                log_level=log_level.lower(),
            )

            uvicorn_server = uvicorn.Server(config)

            print(
                f"Starting Uvicorn server at http://{host}:{port} with log-level {log_level}..."
            )
            try:
                await uvicorn_server.serve()
            finally:
                print("Uvicorn server has stopped.")
                # The app_lifespan's finally block handles mcp_client shutdown

    try:
        asyncio.run(run_server_async())
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}", file=sys.stderr)
        sys.exit(1)


def get_agent_card(host: str, port: int):
    """Returns the Agent Card for the Currency Agent."""
    capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
    skill = AgentSkill(
        id="airbnb_search",
        name="Search airbnb accommodation",
        description="Searches for Airbnb accommodations that are fully available between check-in and checkout dates",
        tags=["airbnb accommodation"],
        examples=[
            "Please find a room in LA, CA, April 15, 2025, checkout date is april 18, 2 adults"
        ],
    )
    return AgentCard(
        name="Airbnb Agent",
        description="Helps with searching accommodation",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=AirbnbAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=AirbnbAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )


@click.command()
@click.option(
    "--host", "host", default=DEFAULT_HOST, help="Hostname to bind the server to."
)
@click.option(
    "--port", "port", default=DEFAULT_PORT, type=int, help="Port to bind the server to."
)
@click.option("--log-level", "log_level", default=DEFAULT_LOG_LEVEL, help="Uvicorn log level.")
def cli(host: str, port: int, log_level: str):
    main(host, port, log_level)

if __name__ == "__main__":
    cli()
from typing import Annotated, Tuple, Optional
from urllib.parse import urlparse, urlunparse
import os
import json
from datetime import datetime
import re

import markdownify
import readabilipy.simple_json
from mcp.shared.exceptions import McpError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    ErrorData,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)
from pydantic import BaseModel, Field, AnyUrl

DEFAULT_USER_AGENT_AUTONOMOUS = "ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)"
DEFAULT_USER_AGENT_MANUAL = "ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)"


def extract_content_from_html(html: str) -> str:
    """Extract and convert HTML content to Markdown format.

    Args:
        html: Raw HTML content to process

    Returns:
        Simplified markdown version of the content
    """
    ret = readabilipy.simple_json.simple_json_from_html_string(
        html, use_readability=True
    )
    if not ret["content"]:
        return "<error>Page failed to be simplified from HTML</error>"
    content = markdownify.markdownify(
        ret["content"],
        heading_style=markdownify.ATX,
    )
    return content

async def fetch_url(
    url: str, user_agent: str, force_raw: bool = False, proxy_url: str | None = None
) -> Tuple[str, str]:
    """
    Fetch the URL and return the content in a form ready for the LLM, as well as a prefix string with status information.
    """
    from httpx import AsyncClient, HTTPError

    async with AsyncClient(proxies=proxy_url) as client:
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
                timeout=30,
            )
        except HTTPError as e:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"))
        if response.status_code >= 400:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to fetch {url} - status code {response.status_code}",
            ))

        page_raw = response.text

    content_type = response.headers.get("content-type", "")
    is_page_html = (
        "<html" in page_raw[:100] or "text/html" in content_type or not content_type
    )

    if is_page_html and not force_raw:
        return extract_content_from_html(page_raw), ""

    return (
        page_raw,
        f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n",
    )


async def fetch_with_jina_fallback(
    url: str, user_agent: str, force_raw: bool = False, proxy_url: str | None = None
) -> Tuple[str, str]:
    """
    Fetch URL using Jina Reader API first, fallback to original fetch logic if failed.
    """
    from httpx import AsyncClient, HTTPError
    
    # Try Jina Reader API first
    jina_url = f"https://r.jina.ai/{url}"
    
    async with AsyncClient(proxies=proxy_url) as client:
        try:
            response = await client.get(
                jina_url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
                timeout=30,
            )
            
            if response.status_code == 200:
                content = response.text
                # Check if it's a Jina error response
                try:
                    error_data = json.loads(content)
                    if "code" in error_data and error_data.get("data") is None:
                        # This is an error response, fallback to original logic
                        raise Exception(f"Jina API error: {error_data.get('message', 'Unknown error')}")
                except json.JSONDecodeError:
                    # Not JSON, assume it's valid content
                    pass
                
                # Jina Reader already returns markdown content
                return content, "Content fetched via Jina Reader API:\n"
                
        except Exception:
            # Jina failed, fallback to original logic
            pass
    
    # Fallback to original fetch logic
    return await fetch_url(url, user_agent, force_raw, proxy_url)


class Fetch(BaseModel):
    """Parameters for fetching a URL."""

    url: Annotated[AnyUrl, Field(description="URL to fetch")]
    max_length: Annotated[
        int,
        Field(
            default=5000,
            description="Maximum number of characters to return.",
            gt=0,
            lt=1000000,
        ),
    ]
    start_index: Annotated[
        int,
        Field(
            default=0,
            description="On return output starting at this character index, useful if a previous fetch was truncated and more context is required.",
            ge=0,
        ),
    ]
    raw: Annotated[
        bool,
        Field(
            default=False,
            description="Get the actual HTML content of the requested page, without simplification.",
        ),
    ]


class FetchAndSave(BaseModel):
    """Parameters for fetching a URL and saving to file."""

    url: Annotated[AnyUrl, Field(description="URL to fetch")]
    file_path: Annotated[Optional[str], Field(default=None, description="File path to save the content (optional, will auto-generate if not provided)")]
    raw: Annotated[
        bool,
        Field(
            default=False,
            description="Get the actual HTML content of the requested page, without simplification.",
        ),
    ]


def generate_filename_from_url(url: str) -> str:
    """Generate a safe filename from URL."""
    # Extract domain and path
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '')
    path = parsed.path.strip('/')
    
    # Create base filename
    if path:
        # Use last part of path
        filename_base = path.split('/')[-1]
        # Remove file extension if present
        if '.' in filename_base:
            filename_base = filename_base.rsplit('.', 1)[0]
    else:
        filename_base = domain
    
    # Clean filename - remove invalid characters
    filename_base = re.sub(r'[^\w\-_.]', '_', filename_base)
    
    # Add timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return f"{filename_base}_{timestamp}.md"


async def serve(
    custom_user_agent: str | None = None,
    proxy_url: str | None = None,
    work_dir: str = "data",
) -> None:
    """Run the fetch MCP server.

    Args:
        custom_user_agent: Optional custom User-Agent string to use for requests
        proxy_url: Optional proxy URL to use for requests
        work_dir: Working directory for saving files (default: "data")
    """
    server = Server("mcp-fetch")
    user_agent_autonomous = custom_user_agent or DEFAULT_USER_AGENT_AUTONOMOUS
    user_agent_manual = custom_user_agent or DEFAULT_USER_AGENT_MANUAL

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="fetch",
                description="""Fetches a URL from the internet and optionally extracts its contents as markdown.

Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that.""",
                inputSchema=Fetch.model_json_schema(),
            ),
            Tool(
                name="fetch_and_save",
                description="""Fetches a URL from the internet using Jina Reader API (with fallback to standard fetch) and saves the content to a file.

This tool first tries to fetch content using Jina Reader API for better markdown conversion, and falls back to the standard fetch method if Jina fails. Files are saved in the configured working directory. If no file path is specified, an automatic filename will be generated based on the URL.""",
                inputSchema=FetchAndSave.model_json_schema(),
            )
        ]

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="fetch",
                description="Fetch a URL and extract its contents as markdown",
                arguments=[
                    PromptArgument(
                        name="url", description="URL to fetch", required=True
                    )
                ],
            )
        ]

    @server.call_tool()
    async def call_tool(name, arguments: dict) -> list[TextContent]:
        if name == "fetch":
            try:
                args = Fetch(**arguments)
            except ValueError as e:
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            url = str(args.url)
            if not url:
                raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))

            content, prefix = await fetch_url(
                url, user_agent_autonomous, force_raw=args.raw, proxy_url=proxy_url
            )
            original_length = len(content)
            if args.start_index >= original_length:
                content = "<error>No more content available.</error>"
            else:
                truncated_content = content[args.start_index : args.start_index + args.max_length]
                if not truncated_content:
                    content = "<error>No more content available.</error>"
                else:
                    content = truncated_content
                    actual_content_length = len(truncated_content)
                    remaining_content = original_length - (args.start_index + actual_content_length)
                    # Only add the prompt to continue fetching if there is still remaining content
                    if actual_content_length == args.max_length and remaining_content > 0:
                        next_start = args.start_index + actual_content_length
                        content += f"\n\n<error>Content truncated. Call the fetch tool with a start_index of {next_start} to get more content.</error>"
            return [TextContent(type="text", text=f"{prefix}Contents of {url}:\n{content}")]
        
        elif name == "fetch_and_save":
            try:
                args = FetchAndSave(**arguments)
            except ValueError as e:
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            url = str(args.url)
            if not url:
                raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))
            
            # Debug: Log received arguments
            debug_info = f"Received arguments: url={url}, file_path={args.file_path}, raw={args.raw}"
            
            # Generate file path if not provided
            if args.file_path and args.file_path.strip():
                # Use provided file path, but ensure it's within work_dir
                provided_path = args.file_path.strip()
                if os.path.isabs(provided_path):
                    # If absolute path, use as-is (user responsibility)
                    file_path = provided_path
                    debug_info += f"\nUsing absolute path: {file_path}"
                else:
                    # If relative path, make it relative to work_dir
                    file_path = os.path.join(work_dir, provided_path)
                    debug_info += f"\nUsing relative path in work_dir: {file_path}"
            else:
                # Auto-generate filename
                filename = generate_filename_from_url(url)
                file_path = os.path.join(work_dir, filename)
                debug_info += f"\nAuto-generated filename: {file_path}"

            try:
                content, prefix = await fetch_with_jina_fallback(
                    url, user_agent_autonomous, force_raw=args.raw, proxy_url=proxy_url
                )
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Save content to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return [TextContent(type="text", text=f"Successfully fetched content from {url} and saved to {file_path}\n\nDebug info: {debug_info}\n\n{prefix}Content preview (first 500 chars):\n{content[:500]}{'...' if len(content) > 500 else ''}")]
                
            except Exception as e:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch and save: {str(e)}"))
        
        else:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Unknown tool: {name}"))

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        if not arguments or "url" not in arguments:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))

        url = arguments["url"]

        try:
            content, prefix = await fetch_url(url, user_agent_manual, proxy_url=proxy_url)
            # TODO: after SDK bug is addressed, don't catch the exception
        except McpError as e:
            return GetPromptResult(
                description=f"Failed to fetch {url}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=str(e)),
                    )
                ],
            )
        return GetPromptResult(
            description=f"Contents of {url}",
            messages=[
                PromptMessage(
                    role="user", content=TextContent(type="text", text=prefix + content)
                )
            ],
        )

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
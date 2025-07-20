# Context MCP Server

A Model Context Protocol (MCP) server that provides intelligent context management and web content fetching capabilities. This server enables AI assistants to efficiently store, retrieve, and manage contextual data while also fetching web content for real-time information access.

## Features

- 🔍 **Smart Content Fetching**: Retrieve web content using Jina Reader API with fallback mechanisms
- 🌐 **Web Content Processing**: Convert HTML to markdown for better AI consumption
- 💾 **File Management**: Save fetched content to organized file structures
- 🚀 **High Performance**: Optimized fetching algorithms with intelligent caching
- 🔧 **Easy Integration**: Standard MCP protocol compatibility with various AI clients

## Available Tools

### fetch

Fetches content from a URL and returns it as text. This tool attempts to get content using the Jina Reader API first, and falls back to direct HTTP request if that fails.

**Arguments:**
- `url` (string, required): The URL to fetch content from
- `max_length` (integer, optional): Maximum number of characters to return (default: 5000)
- `start_index` (integer, optional): Start content from this character index (default: 0)
- `raw` (boolean, optional): Get raw content without markdown conversion (default: false)

**Returns:**
- The content of the URL as text

**Example usage:**
```
Please fetch the content from https://example.com
```

### fetch_and_save

Fetches content from a URL and saves it to a file. This tool attempts to get content using the Jina Reader API first, and falls back to direct HTTP request if that fails.

**Arguments:**
- `url` (string, required): The URL to fetch content from
- `file_path` (string, optional): The path where to save the file. If not provided, a filename will be automatically generated based on the URL domain and timestamp
- `raw` (boolean, optional): Get raw content without markdown conversion (default: false)

**Returns:**
- The path where the file was saved

**Example usage:**
```
Please fetch and save the content from https://example.com to article.txt
```

Or with automatic naming:
```
Please fetch and save the content from https://example.com
```

## Available Prompts

- **fetch**
  - Fetch a URL and extract its contents as markdown
  - Arguments:
    - `url` (string, required): URL to fetch

## Installation and Usage

### Local Development Setup

1. **Clone or download the source code:**
   ```bash
   git clone https://github.com/LangGPT/context-mcp-server.git
   cd context-mcp-server
   ```

2. **Install dependencies using uv:**
   ```bash
   uv sync
   ```

3. **Test the server:**
   ```bash
   uv run python -m context_mcp_server --help
   ```

### Using with Claude Desktop (Local Source)

Add this configuration to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "context-mcp-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/your/context-mcp-server",
        "python",
        "-m",
        "context_mcp_server"
      ],
      "env": {
        "CONTEXT_DIR": "/path/to/your/data/directory"
      }
    }
  }
}
```

**Configuration file locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

### Using with VS Code (Local Source)

Add to your VS Code settings or `.vscode/mcp.json`:

```json
{
  "mcp": {
    "servers": {
      "context-mcp-server": {
        "command": "uv",
        "args": [
          "run",
          "--directory",
          "/path/to/your/context-mcp-server",
          "python",
          "-m",
          "context_mcp_server"
        ],
        "env": {
          "CONTEXT_DIR": "/path/to/your/data/directory"
        }
      }
    }
  }
}
```

### Installation via Package Manager

#### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *context-mcp-server*:

```bash
uvx context-mcp-server
```

#### Using pip

```bash
pip install context-mcp-server
```

After installation, run it as:
```bash
python -m context_mcp_server
```

### Package Manager Configuration

#### Claude Desktop with uvx

```json
{
  "mcpServers": {
    "context-mcp-server": {
      "command": "uvx",
      "args": ["context-mcp-server"],
      "env": {
        "CONTEXT_DIR": "/path/to/your/data/directory"
      }
    }
  }
}
```

#### VS Code with uvx

```json
{
  "mcp": {
    "servers": {
      "context-mcp-server": {
        "command": "uvx",
        "args": ["context-mcp-server"],
        "env": {
          "CONTEXT_DIR": "/path/to/your/data/directory"
        }
      }
    }
  }
}
```

## Configuration

### Environment Variables

#### CONTEXT_DIR

Sets the working directory where files will be saved when using the `fetch_and_save` tool.

- **Default**: `data`
- **Priority**: Command line `--work-dir` argument > `CONTEXT_DIR` environment variable > default value `data`

**Example:**
```bash
export CONTEXT_DIR=/path/to/your/data
```

### Command Line Arguments

#### --work-dir

Specifies the working directory where files will be saved. This overrides the `CONTEXT_DIR` environment variable.

**Example:**
```bash
python -m context_mcp_server --work-dir /custom/path
```

#### --user-agent

By default, depending on if the request came from the model (via a tool), or was user initiated (via a prompt), the server will use either the user-agent:
```
ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)
```
or:
```
ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)
```

This can be customized by adding the argument `--user-agent=YourUserAgent` to the `args` list in the configuration.

#### --proxy-url

The server can be configured to use a proxy by using the `--proxy-url` argument.

## Development

### Setting up Development Environment

1. **Install development dependencies:**
   ```bash
   uv sync --dev
   ```

2. **Run linting and type checking:**
   ```bash
   uv run ruff check
   uv run pyright
   ```

3. **Build the package:**
   ```bash
   uv build
   ```

### Testing

Test the server locally:
```bash
uv run python -m context_mcp_server
```

With custom work directory:
```bash
uv run python -m context_mcp_server --work-dir /custom/path
```

With environment variable:
```bash
CONTEXT_DIR=/custom/path uv run python -m context_mcp_server
```

Use the MCP inspector for debugging:
```bash
npx @modelcontextprotocol/inspector uv run python -m context_mcp_server
```

With custom work directory:
```bash
npx @modelcontextprotocol/inspector uv run python -m context_mcp_server --work-dir /custom/path
```

### Making Changes

1. Edit the source code in `src/context_mcp_server/`
2. Test your changes with `uv run python -m context_mcp_server`
3. Update version in `pyproject.toml` if needed
4. Run tests and linting

## Debugging

You can use the MCP inspector to debug the server:

For local development:
```bash
npx @modelcontextprotocol/inspector uv run python -m context_mcp_server
```

For uvx installations:
```bash
npx @modelcontextprotocol/inspector uvx context-mcp-server
```

## Contributing

We encourage contributions to help expand and improve context-mcp-server. Whether you want to add new tools, enhance existing functionality, or improve documentation, your input is valuable.

## License

context-mcp-server is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
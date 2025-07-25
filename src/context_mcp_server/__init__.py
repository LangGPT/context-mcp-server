from .server import serve


def main():
    """MCP Fetch Server - HTTP fetching functionality for MCP"""
    import argparse
    import asyncio
    import os

    parser = argparse.ArgumentParser(
        description="give a model the ability to make web requests"
    )
    parser.add_argument("--user-agent", type=str, help="Custom User-Agent string")
    parser.add_argument("--proxy-url", type=str, help="Proxy URL to use for requests")

    args = parser.parse_args()
    asyncio.run(serve(args.user_agent, args.proxy_url))


if __name__ == "__main__":
    main()

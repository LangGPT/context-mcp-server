from .server import serve


def main():
    """MCP Fetch Server - HTTP fetching functionality for MCP"""
    import argparse
    import asyncio
    import os

    # Get default work directory from environment variable or use 'data' as fallback
    default_work_dir = os.environ.get('CONTEXT_DIR', 'data')

    parser = argparse.ArgumentParser(
        description="give a model the ability to make web requests"
    )
    parser.add_argument("--user-agent", type=str, help="Custom User-Agent string")
    parser.add_argument("--proxy-url", type=str, help="Proxy URL to use for requests")
    parser.add_argument("--work-dir", type=str, default=default_work_dir, help=f"Working directory for saving files (default: {default_work_dir})")

    args = parser.parse_args()
    asyncio.run(serve(args.user_agent, args.proxy_url, args.work_dir))


if __name__ == "__main__":
    main()

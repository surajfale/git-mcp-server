"""Entry point for running the Git Commit MCP Server."""

from git_commit_mcp.server import mcp


def main():
    """Main entry point for the MCP server."""
    # Run with stdio transport for MCP client communication
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

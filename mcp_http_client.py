#!/usr/bin/env python3
"""
MCP HTTP Client Wrapper
Bridges stdio MCP protocol to HTTP transport for remote MCP servers.
"""
import sys
import json
import requests
import logging
from typing import Any, Dict, Optional

# Configuration
MCP_SERVER_URL = "https://git-mcp-server-production-9d2a.up.railway.app/mcp"
AUTH_TOKEN = "dQqUICX5CTiwvAGs3dnAwCJnfvCyld60FDqDYho1fTc="

# Setup logging to stderr so it doesn't interfere with stdio
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class MCPHTTPClient:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        self.request_id = 0
    
    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Optional[int] = None) -> Dict[str, Any]:
        """Send JSON-RPC request to HTTP MCP server."""
        if request_id is None:
            self.request_id += 1
            request_id = self.request_id
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        logger.debug(f"Sending request: {method}")
        
        try:
            response = self.session.post(self.url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Received response for {method}")
            return result
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {method}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Request timed out"
                },
                "id": request_id
            }
        except Exception as e:
            logger.error(f"Request failed for {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"HTTP request failed: {str(e)}"
                },
                "id": request_id
            }

def main():
    """Main stdio loop - reads from stdin, sends to HTTP server, writes to stdout."""
    logger.info("MCP HTTP Client starting")
    client = MCPHTTPClient(MCP_SERVER_URL, AUTH_TOKEN)
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            try:
                request = json.loads(line)
                method = request.get("method")
                params = request.get("params")
                request_id = request.get("id")
                
                logger.debug(f"Processing request: {method} (id={request_id})")
                
                # Forward to HTTP server
                response = client.send_request(method, params, request_id)
                
                # Write response to stdout
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    },
                    "id": None
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": None
                }
                print(json.dumps(error_response), flush=True)
    except KeyboardInterrupt:
        logger.info("MCP HTTP Client shutting down")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

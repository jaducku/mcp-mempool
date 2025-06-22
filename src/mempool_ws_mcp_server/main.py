"""Mempool WebSocket MCP Server - FastMCP 구현."""

import asyncio
import logging
import sys

import structlog

from .config import config
from .tools import create_mcp_server, initialize_websocket

# 로깅 설정
logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def main():
    """메인 함수 - MCP 서버를 Streamable HTTP 모드로 실행."""
    try:
        # WebSocket 초기화
        asyncio.run(initialize_websocket())
        
        # FastMCP 서버 인스턴스 가져오기
        mcp_server = create_mcp_server()
        
        # MCP 서버를 Streamable HTTP 모드로 실행
        logger.info("Starting FastMCP server in Streamable HTTP mode", 
                   host=config.HOST, port=config.PORT)
        
        mcp_server.run(
            transport="streamable-http", 
            host=config.HOST, 
            port=config.PORT, 
            path="/mcp"
        )
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Server startup failed", error=str(e))
        sys.exit(1)


def main_stdio():
    """STDIO 모드로 MCP 서버 실행."""
    try:
        # WebSocket 초기화
        asyncio.run(initialize_websocket())
        
        # FastMCP 서버 인스턴스 가져오기
        mcp_server = create_mcp_server()
        
        # MCP 서버를 STDIO 모드로 실행
        logger.info("Starting FastMCP server in STDIO mode")
        mcp_server.run()
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Server startup failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    # 인자에 따라 다른 모드로 실행
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        main_stdio()
    else:
        main()  # 기본적으로 Streamable HTTP 모드 
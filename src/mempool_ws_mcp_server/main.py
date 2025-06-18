"""Mempool WebSocket MCP Server - FastMCP 구현."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import config
from .tools import create_mcp_server, initialize_websocket, ws_manager

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI 라이프사이클 관리."""
    logger.info("Starting Mempool WebSocket MCP Server")
    
    try:
        # WebSocket 연결 초기화
        await initialize_websocket()
        logger.info("Server startup completed")
        yield
    except Exception as e:
        logger.error("Failed to start server", error=str(e))
        raise
    finally:
        # 정리 작업
        logger.info("Shutting down server")
        try:
            await ws_manager.disconnect()
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


# FastAPI 앱 생성
app = FastAPI(
    title="Mempool WebSocket MCP Server",
    description="비트코인 mempool.space WebSocket API를 위한 MCP 서버",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
if config.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트."""
    try:
        status = await ws_manager.get_connection_status()
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "websocket_connected": status["connected"],
                "active_subscriptions": status.get("active_subscriptions", 0),
                "server": "Mempool WebSocket MCP Server"
            }
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "server": "Mempool WebSocket MCP Server"
            }
        )


@app.get("/")
async def root():
    """루트 엔드포인트."""
    return {
        "message": "Mempool WebSocket MCP Server",
        "version": "1.0.0",
        "description": "비트코인 mempool.space WebSocket API를 위한 MCP 서버",
        "endpoints": {
            "health": "/health",
            "mcp": "stdio 또는 fastmcp 명령어로 실행"
        }
    }


def main():
    """메인 함수 - MCP 서버를 Streamable HTTP 모드로 실행."""
    try:
        # FastMCP 서버 인스턴스 가져오기
        mcp_server = create_mcp_server()
        
        # MCP 서버를 Streamable HTTP 모드로 실행 (표준)
        logger.info("Starting FastMCP server in Streamable HTTP mode", 
                   host=config.HOST, port=config.PORT)
        mcp_server.run(transport="streamable-http", host=config.HOST, port=config.PORT, path="/mcp")
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Server startup failed", error=str(e))
        sys.exit(1)


def main_stdio():
    """STDIO 모드로 MCP 서버 실행."""
    try:
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


def run_http_server():
    """HTTP 서버 실행 (개발용)."""
    uvicorn.run(
        "mempool_ws_mcp_server.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    # 인자에 따라 다른 모드로 실행
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        main_stdio()
    else:
        main()  # 기본적으로 Streamable HTTP 모드 
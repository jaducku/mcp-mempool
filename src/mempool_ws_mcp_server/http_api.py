"""HTTP API 서버 - 디버깅 및 상태 확인용."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import config
from .tools import initialize_websocket, ws_manager

# 로깅 설정
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI 라이프사이클 관리."""
    logger.info("Starting HTTP API Server")
    
    try:
        # WebSocket 연결 초기화
        await initialize_websocket()
        logger.info("HTTP API Server startup completed")
        yield
    except Exception as e:
        logger.error("Failed to start HTTP API server", error=str(e))
        raise
    finally:
        # 정리 작업
        logger.info("Shutting down HTTP API server")
        try:
            await ws_manager.disconnect()
        except Exception as e:
            logger.error("Error during HTTP API server shutdown", error=str(e))


# FastAPI 앱 생성
app = FastAPI(
    title="Mempool WebSocket MCP Server - HTTP API",
    description="비트코인 mempool.space WebSocket API를 위한 MCP 서버의 HTTP API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
if config.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if "*" in config.ALLOWED_ORIGINS else config.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"]
    )


@app.get("/")
async def root():
    """루트 엔드포인트."""
    return {
        "message": "Mempool WebSocket MCP Server - HTTP API",
        "version": "1.0.0",
        "description": "비트코인 mempool.space WebSocket API를 위한 MCP 서버의 HTTP API",
        "endpoints": {
            "health": "/health",
            "mcp_info": "/mcp/info",
            "docs": "/docs"
        },
        "mcp_server": {
            "url": f"http://{config.HOST}:8000/mcp",
            "transport": "streamable-http",
            "note": "MCP 서버는 포트 8000에서 실행됩니다"
        }
    }


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
                "server": "Mempool WebSocket MCP Server - HTTP API"
            }
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "server": "Mempool WebSocket MCP Server - HTTP API"
            }
        )


@app.get("/mcp/info")
async def mcp_info():
    """MCP 서버 정보 엔드포인트 (디버깅용)"""
    try:
        ws_status = await ws_manager.get_connection_status()
    except Exception:
        ws_status = {"connected": False, "error": "Failed to get status"}
    
    return {
        "server": "Mempool WebSocket MCP Server",
        "version": "1.0.0",
        "transport": "streamable-http",
        "mcp_endpoint": f"http://{config.HOST}:8000/mcp",
        "available_tools": [
            "subscribe_blocks", "subscribe_mempool_blocks", "subscribe_stats",
            "subscribe_live_chart", "track_address", "get_connection_status",
            "unsubscribe_client", "get_address_info", "get_address_balance",
            "get_address_utxos", "get_address_transactions", "get_recommended_fees",
            "get_mempool_info", "get_transaction_info", "get_block_info",
            "get_block_height", "validate_bitcoin_address"
        ],
        "websocket_status": ws_status,
        "usage_example": {
            "initialize": {
                "method": "POST",
                "url": f"http://{config.HOST}:8000/mcp",
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"}
                    },
                    "id": 1
                }
            }
        }
    }


@app.get("/status")
async def status():
    """시스템 전체 상태"""
    try:
        ws_status = await ws_manager.get_connection_status()
        
        return {
            "timestamp": asyncio.get_event_loop().time(),
            "services": {
                "http_api": {"status": "running", "port": 8001},
                "mcp_server": {"status": "running", "port": 8000},
                "websocket": ws_status
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to get status",
                "details": str(e)
            }
        ) 
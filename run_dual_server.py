#!/usr/bin/env python3
"""
MCP 서버와 HTTP API 서버를 동시에 실행하는 스크립트

이 스크립트는 두 개의 서버를 별도 포트에서 실행합니다:
1. MCP 서버 (포트 8000) - /mcp 엔드포인트
2. HTTP API 서버 (포트 8001) - 디버깅 및 상태 확인용
"""

import asyncio
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import uvicorn
import logging

# 현재 파일의 경로를 기준으로 src 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
# 절대 경로로 변환하여 추가
absolute_src_dir = os.path.abspath(src_dir)
if absolute_src_dir not in sys.path:
    sys.path.insert(0, absolute_src_dir)

# 프로젝트 루트도 추가
project_root = current_dir
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from mempool_ws_mcp_server.tools import create_mcp_server, initialize_websocket
    from mempool_ws_mcp_server.http_api import app
    from mempool_ws_mcp_server.config import config
except ImportError as e:
    print(f"Error importing modules: {e}", file=sys.stderr)
    print("Please ensure all dependencies are installed:", file=sys.stderr)
    print("  pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

import structlog

logger = structlog.get_logger(__name__)

def run_mcp_server():
    """MCP 서버를 별도 스레드에서 실행"""
    try:
        logger.info("Starting MCP server on port 8000")
        mcp_server = create_mcp_server()
        mcp_server.run(
            transport="streamable-http",
            host=config.HOST,
            port=8000,
            path="/mcp"
        )
    except Exception as e:
        logger.error("MCP server failed", error=str(e))

def run_http_server():
    """HTTP API 서버를 별도 스레드에서 실행"""
    try:
        logger.info("Starting HTTP API server on port 8001")
        uvicorn.run(
            app,
            host=config.HOST,
            port=8001,
            log_level="info"
        )
    except Exception as e:
        logger.error("HTTP server failed", error=str(e))

async def initialize_services():
    """서비스 초기화"""
    try:
        await initialize_websocket()
        logger.info("WebSocket initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize WebSocket", error=str(e))
        raise

def main():
    """메인 함수"""
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    try:
        # WebSocket 초기화
        asyncio.run(initialize_services())
        
        # 두 개의 서버를 별도 스레드에서 실행
        with ThreadPoolExecutor(max_workers=2) as executor:
            # MCP 서버 실행
            mcp_future = executor.submit(run_mcp_server)
            
            # HTTP API 서버 실행
            http_future = executor.submit(run_http_server)
            
            print("=== 서버 시작됨 ===")
            print("MCP 서버: http://localhost:8000/mcp")
            print("HTTP API 서버: http://localhost:8001")
            print("상태 확인: http://localhost:8001/health")
            print("MCP 정보: http://localhost:8001/mcp/info")
            print("===================")
            
            # 둘 중 하나라도 종료되면 전체 종료
            try:
                mcp_future.result()
            except KeyboardInterrupt:
                print("\n서버 종료 중...")
            except Exception as e:
                logger.error("MCP server error", error=str(e))
            
            try:
                http_future.result()
            except KeyboardInterrupt:
                print("\n서버 종료 중...")
            except Exception as e:
                logger.error("HTTP server error", error=str(e))
                
    except KeyboardInterrupt:
        print("\n사용자에 의해 서버가 중단되었습니다.")
    except Exception as e:
        logger.error("서버 시작 실패", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main() 
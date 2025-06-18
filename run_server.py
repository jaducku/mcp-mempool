#!/usr/bin/env python3
"""
Mempool WebSocket MCP Server 실행 스크립트

uvx로 실행하기 위한 엔트리 포인트입니다.

사용법:
    python run_server.py                 # Streamable HTTP 모드 (기본, port 8000/mcp)
    python run_server.py stdio           # STDIO 모드
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 메인 모듈 임포트 및 실행
if __name__ == "__main__":
    try:
        from mempool_ws_mcp_server.main import main, main_stdio
        
        # 인자에 따라 다른 모드로 실행
        if len(sys.argv) > 1 and sys.argv[1] == "stdio":
            print("STDIO 모드로 실행 중...")
            main_stdio()
        else:
            print("Streamable HTTP 모드로 실행 중... (포트 8000, 엔드포인트 /mcp)")
            main()
            
    except ImportError as e:
        print(f"Import 오류: {e}")
        print("의존성을 설치했는지 확인해주세요:")
        print("uv pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"서버 실행 오류: {e}")
        sys.exit(1) 
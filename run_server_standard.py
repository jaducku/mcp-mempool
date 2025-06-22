#!/usr/bin/env python3
"""
Claude Desktop 호환성을 위한 표준 MCP 서버 실행 스크립트

이 스크립트는 표준 MCP 라이브러리를 사용하여 STDIO 모드로 서버를 실행합니다.
Claude Desktop에서 직접 사용할 수 있도록 최적화되었습니다.
"""

import sys
import os
import asyncio
import logging

# 현재 파일의 경로를 기준으로 src 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, src_dir)

try:
    from mempool_ws_mcp_server.standard_mcp_server import main
except ImportError as e:
    print(f"Error importing MCP server: {e}", file=sys.stderr)
    print("Please ensure all dependencies are installed:", file=sys.stderr)
    print("  pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    # 로깅 레벨 설정 (Claude Desktop 호환성을 위해 ERROR만 표시)
    logging.basicConfig(
        level=logging.ERROR,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr
    )
    
    try:
        main()
    except Exception as e:
        print(f"서버 실행 실패: {e}", file=sys.stderr)
        sys.exit(1) 
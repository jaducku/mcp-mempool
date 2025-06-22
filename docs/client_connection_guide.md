# MCP 클라이언트 연결 가이드

## 개요

Mempool WebSocket MCP 서버는 FastMCP의 streamable-http 모드로 실행됩니다. 클라이언트가 올바르게 연결하려면 MCP 프로토콜을 따라야 합니다.

## 서버 정보

- **URL**: `http://localhost:8000/mcp`
- **Transport**: streamable-http
- **Protocol**: MCP (Model Context Protocol)

## 문제 해결

### 307 Temporary Redirect 오류

클라이언트가 OPTIONS 요청을 보낼 때 발생하는 문제입니다. 이는 CORS preflight 요청 때문입니다.

**해결책**: 서버에서 `/mcp` 엔드포인트에 대한 OPTIONS 요청을 처리하도록 수정했습니다.

### 406 Not Acceptable / 405 Method Not Allowed 오류

일반 HTTP 요청으로 MCP 엔드포인트에 접근할 때 발생합니다.

**해결책**: MCP 프로토콜에 맞는 요청을 보내야 합니다.

## MCP 클라이언트 연결 방법

### 1. JavaScript/TypeScript 클라이언트

```javascript
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

// HTTP 전송을 위한 클라이언트 설정
const client = new Client({
  name: "mempool-client",
  version: "1.0.0"
});

// streamable-http 연결
const response = await fetch('http://localhost:8000/mcp', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    jsonrpc: '2.0',
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'mempool-client',
        version: '1.0.0'
      }
    },
    id: 1
  })
});
```

### 2. Python 클라이언트

```python
import asyncio
import json
import aiohttp

async def connect_to_mcp():
    async with aiohttp.ClientSession() as session:
        # 초기화 요청
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mempool-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        async with session.post(
            'http://localhost:8000/mcp',
            json=init_request,
            headers={'Content-Type': 'application/json'}
        ) as response:
            result = await response.json()
            print("Initialize response:", result)
        
        # 도구 목록 요청
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        
        async with session.post(
            'http://localhost:8000/mcp',
            json=tools_request,
            headers={'Content-Type': 'application/json'}
        ) as response:
            result = await response.json()
            print("Tools list:", result)

# 실행
asyncio.run(connect_to_mcp())
```

### 3. cURL 테스트

```bash
# 1. 초기화
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "curl-client",
        "version": "1.0.0"
      }
    },
    "id": 1
  }'

# 2. 도구 목록
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 2
  }'

# 3. 도구 호출 (예: 현재 블록 높이)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_block_height",
      "arguments": {}
    },
    "id": 3
  }'
```

## 사용 가능한 도구들

- `subscribe_blocks` - 블록 정보 구독
- `subscribe_mempool_blocks` - 멤풀 블록 정보 구독
- `subscribe_stats` - 통계 정보 구독
- `subscribe_live_chart` - 실시간 차트 데이터 구독
- `track_address` - 주소 추적
- `get_connection_status` - WebSocket 연결 상태 확인
- `unsubscribe_client` - 구독 해제
- `get_address_info` - 주소 정보 조회
- `get_address_balance` - 주소 잔액 조회
- `get_address_utxos` - 주소 UTXO 목록
- `get_address_transactions` - 주소 거래 내역
- `get_recommended_fees` - 추천 수수료
- `get_mempool_info` - 멤풀 정보
- `get_transaction_info` - 거래 정보
- `get_block_info` - 블록 정보
- `get_block_height` - 현재 블록 높이
- `validate_bitcoin_address` - 주소 검증

## 디버깅 엔드포인트

서버 상태와 정보를 확인할 수 있는 추가 엔드포인트들:

- `GET /` - 서버 기본 정보
- `GET /health` - 헬스 체크
- `GET /mcp/info` - MCP 서버 상세 정보
- `GET /docs` - FastAPI 문서

## 주의사항

1. MCP 프로토콜은 JSON-RPC 2.0을 기반으로 합니다
2. 모든 요청은 POST 메서드를 사용해야 합니다
3. Content-Type은 `application/json`이어야 합니다
4. CORS가 활성화되어 있어 브라우저에서도 접근 가능합니다 
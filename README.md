# MCP Mempool 🚀

**비트코인 mempool.space WebSocket & REST API를 위한 Model Context Protocol (MCP) 서버**

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Bitcoin](https://img.shields.io/badge/Bitcoin-FF9900?style=for-the-badge&logo=bitcoin&logoColor=white)](https://bitcoin.org)

## 📋 개요

MCP Mempool은 mempool.space의 WebSocket과 REST API를 MCP (Model Context Protocol) 형태로 래핑하여 AI Agent와 외부 애플리케이션이 비트코인 네트워크 데이터를 쉽게 활용할 수 있도록 하는 서버입니다.

### ✨ 주요 기능

#### 🔄 WebSocket 기능 (실시간)
- **실시간 블록 데이터**: 새 블록 생성 시 즉시 알림
- **멤풀 블록 템플릿**: 예상되는 다음 블록 정보
- **네트워크 통계**: 메모리풀 상태 실시간 모니터링  
- **주소 추적**: 특정 비트코인 주소의 거래 실시간 추적
- **라이브 차트**: 수수료 변화 추이 실시간 데이터

#### 🔍 REST API 기능 (쿼리)
- **주소 정보 조회**: 잔액, 거래 내역, UTXO 목록
- **거래 정보**: 개별 거래 상세 정보 및 상태
- **블록 데이터**: 블록 정보, 거래 목록, 최신 높이
- **수수료 정보**: 추천 수수료율, 멤풀 블록별 수수료
- **멤풀 상태**: 현재 멤풀 정보 및 최근 거래
- **주소 검증**: 비트코인 주소 유효성 검사

## 🚀 빠른 시작

### Docker로 실행 (권장)

```bash
# 개발 환경
docker-compose up mcp-mempool-dev

# 프로덕션 환경  
docker-compose up mcp-mempool-prod
```

서버가 실행되면 http://localhost:8000 에서 접근 가능합니다.

### 로컬 설치

```bash
# 의존성 설치
uv sync

# 서버 실행
uv run python -m mempool_ws_mcp_server.main
```

## 🔧 환경 변수 설정

```bash
# 서버 설정
MCP_HOST=0.0.0.0                      # 서버 호스트
MCP_PORT=8000                         # 서버 포트
LOG_LEVEL=INFO                        # 로그 레벨

# Mempool API 설정
MEMPOOL_WS_URL=wss://mempool.space/api/v1/ws    # WebSocket URL
MEMPOOL_API_URL=https://mempool.space/api       # REST API URL

# WebSocket 설정
WS_RECONNECT_INTERVAL=5               # 재연결 간격 (초)
WS_MAX_RECONNECT_ATTEMPTS=10          # 최대 재연결 시도
WS_PING_INTERVAL=30                   # Ping 간격 (초)
WS_PING_TIMEOUT=10                    # Ping 타임아웃 (초)

# HTTP 클라이언트 설정
HTTP_TIMEOUT=30                       # HTTP 요청 타임아웃 (초)
HTTP_MAX_RETRIES=3                    # 최대 재시도 횟수

# 성능 설정
MAX_MESSAGE_QUEUE_SIZE=1000           # 메시지 큐 최대 크기
MESSAGE_BATCH_SIZE=10                 # 메시지 배치 크기

# 보안 설정
CORS_ENABLED=true                     # CORS 활성화
ALLOWED_ORIGINS=*                     # 허용된 오리진 (콤마 구분)

# 개발 모드
DEBUG=false                           # 디버그 모드
RELOAD=false                          # 자동 재시작
```

## 🛠 MCP 클라이언트 설정

### Claude Desktop

`claude_desktop_config.json` 파일에 추가:

```json
{
  "mcpServers": {
    "mcp-mempool": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8000/mcp"]
    }
  }
}

{
  "mcpServers": {
    "mcp-mempool": {
      "transport": "streamable-http",
      "url" : "http://127.0.0.1:8000/mcp" //배포시 실제 서빙 url
    }
  }
}

```

### Amazon Q Developer

`.aws/amazonq/mcp.json` 파일에 추가:

```json
{
  "mcpServers": {
    "mcp-mempool": {
      "command": "npx", 
      "args": ["mcp-remote", "http://localhost:8000/mcp"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## 📡 사용 가능한 도구들

### WebSocket 도구 (실시간 스트리밍)

#### `subscribe_blocks`
새 블록 생성 시 실시간 알림을 받습니다.

#### `subscribe_mempool_blocks` 
예상되는 다음 블록 템플릿 정보를 실시간으로 받습니다.

#### `subscribe_stats`
네트워크 메모리풀 통계를 실시간으로 모니터링합니다.

#### `subscribe_live_chart`
2시간 라이브 수수료 차트 데이터를 실시간으로 받습니다.

#### `track_address`
특정 비트코인 주소의 거래를 실시간으로 추적합니다.
- `address`: 추적할 비트코인 주소

#### `get_connection_status`
WebSocket 연결 상태를 확인합니다.

#### `unsubscribe_client`
클라이언트의 모든 구독을 해제합니다.
- `client_id`: 구독 해제할 클라이언트 ID

### REST API 도구 (쿼리)

#### 주소 관련

**`get_address_info`** - 주소의 모든 정보 조회
- `address`: 비트코인 주소

**`get_address_balance`** - 주소 잔액 조회  
- `address`: 비트코인 주소

**`get_address_utxos`** - 주소의 UTXO 목록 조회
- `address`: 비트코인 주소

**`get_address_transactions`** - 주소의 거래 내역 조회
- `address`: 비트코인 주소
- `after_txid` (선택): 특정 거래 이후의 거래들만 조회

#### 거래 관련

**`get_transaction_info`** - 거래 정보 조회
- `txid`: 거래 ID

**`get_block_info`** - 블록 정보 조회  
- `hash_or_height`: 블록 해시 또는 높이

**`get_block_height`** - 현재 블록 높이 조회

#### 수수료 & 멤풀

**`get_recommended_fees`** - 추천 수수료율 조회

**`get_mempool_info`** - 현재 멤풀 정보 조회

#### 유틸리티

**`validate_bitcoin_address`** - 비트코인 주소 유효성 검사
- `address`: 검증할 주소

## 💻 사용 예시

### 주소 잔액 조회

```bash
# MCP 클라이언트에서 사용
get_address_balance address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
```

### 실시간 수수료 모니터링

```bash
# 실시간 멤풀 블록 구독
subscribe_mempool_blocks

# 추천 수수료 조회
get_recommended_fees
```

### 주소 추적

```bash
# 특정 주소 실시간 추적
track_address address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
```

## 🏗 개발

### 개발 환경 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd mcp-mempool

# 개발 의존성 설치
uv sync --dev

# 개발 서버 실행
uv run python -m mempool_ws_mcp_server.main
```

### 테스트 실행

```bash
# 모든 테스트 실행
uv run pytest

# 커버리지 포함
uv run pytest --cov=mempool_ws_mcp_server
```

### 코드 품질 도구

```bash
# 린팅
uv run ruff check .

# 포맷팅
uv run ruff format .

# 타입 체크
uv run mypy src/
```

## 🐳 Docker 빌드

```bash
# 이미지 빌드
docker build -t mcp-mempool .

# 멀티 아키텍처 빌드
docker buildx build --platform linux/amd64,linux/arm64 -t mcp-mempool .
```

## 📊 모니터링

```bash
# 모니터링 스택 실행 (Prometheus + Grafana)
docker-compose --profile monitoring up

# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

## 🔗 API 엔드포인트

- **Health Check**: `GET /health`
- **Root Info**: `GET /`  
- **MCP Protocol**: `POST /mcp`
- **API Docs**: `GET /docs`

## 📄 라이선스

MIT License

## 🤝 기여

이슈 리포트와 풀 리퀘스트를 환영합니다!

## 📞 지원

- 문제가 있으시면 GitHub Issues를 활용해주세요
- 개선 제안이나 새로운 기능 요청도 환영합니다 

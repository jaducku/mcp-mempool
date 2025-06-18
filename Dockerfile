# ==================================================
# 멀티스테이지 빌드를 통한 Docker 이미지 최적화
# ==================================================

# 빌드 스테이지
FROM python:3.11-slim as builder

# 빌드 도구 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# uv 설치 (빠른 Python 패키지 매니저)
RUN pip install --no-cache-dir uv

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일만 먼저 복사 (Docker 레이어 캐싱 최적화)
COPY pyproject.toml uv.lock ./

# 의존성 설치 (프로덕션 의존성만)
RUN uv sync --frozen --no-dev

# 소스코드 복사
COPY src/ ./src/
COPY README.md ./

# 애플리케이션 빌드/설치
RUN uv build

# ==================================================
# 프로덕션 스테이지
FROM python:3.11-slim as production

# 시스템 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# 비 root 유저 생성 (보안 강화)
ARG UID=1001
ARG GID=1001
RUN groupadd -g $GID appuser && \
    useradd -u $UID -g $GID -s /bin/bash -m appuser

# 작업 디렉토리 설정
WORKDIR /app

# uv 설치
RUN pip install --no-cache-dir uv

# 빌드 스테이지에서 가상환경과 애플리케이션 복사
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# 환경변수 설정
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 애플리케이션 설정 가능한 환경변수들
ENV MEMPOOL_WS_URL="wss://mempool.space/api/v1/ws"
ENV MEMPOOL_API_URL="https://mempool.space/api"
ENV MCP_PORT=8000
ENV MCP_HOST="0.0.0.0"
ENV LOG_LEVEL="INFO"

# 앱 디렉토리 권한 설정
RUN chown -R appuser:appuser /app

# 비 root 유저로 전환
USER appuser

# 포트 노출
EXPOSE $MCP_PORT

# 헬스체크 설정 (개선된 버전)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:$MCP_PORT/health || exit 1

# 애플리케이션 실행
CMD ["python", "-m", "mempool_ws_mcp_server.main"] 
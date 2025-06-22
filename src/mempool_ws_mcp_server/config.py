"""환경변수 기반 설정 관리."""

import os
from typing import Optional


class Config:
    """애플리케이션 설정 클래스."""
    
    # 서버 설정
    HOST: str = os.getenv("MCP_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("MCP_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Mempool API 설정
    MEMPOOL_WS_URL: str = os.getenv("MEMPOOL_WS_URL", "wss://mempool.space/api/v1/ws")
    MEMPOOL_API_URL: str = os.getenv("MEMPOOL_API_URL", "https://mempool.space/api")
    
    # WebSocket 설정
    WS_RECONNECT_INTERVAL: int = int(os.getenv("WS_RECONNECT_INTERVAL", "5"))
    WS_MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("WS_MAX_RECONNECT_ATTEMPTS", "10"))
    WS_PING_INTERVAL: int = int(os.getenv("WS_PING_INTERVAL", "30"))
    WS_PING_TIMEOUT: int = int(os.getenv("WS_PING_TIMEOUT", "10"))
    
    # HTTP 클라이언트 설정
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))
    HTTP_MAX_RETRIES: int = int(os.getenv("HTTP_MAX_RETRIES", "3"))
    
    # 성능 설정
    MAX_MESSAGE_QUEUE_SIZE: int = int(os.getenv("MAX_MESSAGE_QUEUE_SIZE", "1000"))
    MESSAGE_BATCH_SIZE: int = int(os.getenv("MESSAGE_BATCH_SIZE", "10"))
    
    # 보안 설정
    ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    CORS_ENABLED: bool = os.getenv("CORS_ENABLED", "true").lower() == "true"
    
    # 개발 모드
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    RELOAD: bool = os.getenv("RELOAD", "false").lower() == "true"
    
    @classmethod
    def get_log_config(cls) -> dict:
        """로깅 설정을 반환합니다."""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                },
                "json": {
                    "()": "structlog.stdlib.ProcessorFormatter",
                    "processor": "structlog.dev.ConsoleRenderer(colors=False)",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": cls.LOG_LEVEL,
                "handlers": ["default"],
            },
            "loggers": {
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["default"],
                    "propagate": False,
                },
                "websockets": {
                    "level": "WARNING",
                    "handlers": ["default"],
                    "propagate": False,
                },
            },
        }


# 글로벌 설정 인스턴스
config = Config() 
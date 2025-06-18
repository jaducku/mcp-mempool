"""Pydantic 모델과 타입 정의."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ChannelType(str, Enum):
    """WebSocket 채널 타입."""
    BLOCKS = "blocks"
    MEMPOOL_BLOCKS = "mempool-blocks"
    STATS = "stats"
    LIVE_2H_CHART = "live-2h-chart"
    TRACK_ADDRESS = "track-address"


class WebSocketMessage(BaseModel):
    """WebSocket 메시지 모델."""
    action: str = Field(..., description="액션 타입")
    data: List[str] = Field(default_factory=list, description="구독할 채널 목록")


class TrackAddressMessage(BaseModel):
    """주소 추적 메시지 모델."""
    track_address: str = Field(..., description="추적할 주소")


class BlockData(BaseModel):
    """블록 데이터 모델."""
    height: Optional[int] = Field(None, description="블록 높이")
    hash: Optional[str] = Field(None, description="블록 해시")
    timestamp: Optional[int] = Field(None, description="타임스탬프")
    tx_count: Optional[int] = Field(None, description="트랜잭션 수")
    size: Optional[int] = Field(None, description="블록 크기")
    weight: Optional[int] = Field(None, description="블록 가중치")
    fee_range: Optional[List[int]] = Field(None, description="수수료 범위")


class MempoolStats(BaseModel):
    """메모리풀 통계 모델."""
    count: Optional[int] = Field(None, description="트랜잭션 수")
    vsize: Optional[int] = Field(None, description="가상 크기")
    total_fee: Optional[int] = Field(None, description="총 수수료")
    fee_histogram: Optional[List[List[Union[int, float]]]] = Field(None, description="수수료 히스토그램")


class Live2HData(BaseModel):
    """2시간 라이브 차트 데이터 모델."""
    timestamps: Optional[List[int]] = Field(None, description="타임스탬프 리스트")
    fee_rates: Optional[List[float]] = Field(None, description="수수료율 리스트")


class TransactionData(BaseModel):
    """트랜잭션 데이터 모델."""
    txid: Optional[str] = Field(None, description="트랜잭션 ID")
    fee: Optional[int] = Field(None, description="수수료")
    vsize: Optional[int] = Field(None, description="가상 크기")
    value: Optional[int] = Field(None, description="값")
    status: Optional[Dict[str, Any]] = Field(None, description="상태")


class HealthStatus(BaseModel):
    """헬스 체크 상태 모델."""
    status: str = Field("ok", description="상태")
    timestamp: Optional[int] = Field(None, description="타임스탬프")
    uptime: Optional[float] = Field(None, description="가동 시간")
    websocket_connected: Optional[bool] = Field(None, description="WebSocket 연결 상태")
    active_subscriptions: Optional[int] = Field(None, description="활성 구독 수")


class StreamResponse(BaseModel):
    """스트림 응답 모델."""
    success: bool = Field(..., description="성공 여부")
    message: Optional[str] = Field(None, description="메시지")
    data: Optional[Dict[str, Any]] = Field(None, description="데이터")
    channel: Optional[str] = Field(None, description="채널명")
    timestamp: Optional[int] = Field(None, description="타임스탬프")


class ErrorResponse(BaseModel):
    """에러 응답 모델."""
    error: str = Field(..., description="에러 메시지")
    code: Optional[str] = Field(None, description="에러 코드")
    timestamp: Optional[int] = Field(None, description="타임스탬프")
    details: Optional[Dict[str, Any]] = Field(None, description="에러 상세 정보") 
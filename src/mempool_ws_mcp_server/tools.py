"""FastMCP 도구 정의."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastmcp import FastMCP

from .types import ChannelType, BlockData, MempoolStats, TrackAddressMessage
from .websocket_manager import WebSocketManager
from .rest_client import rest_client

logger = structlog.get_logger(__name__)

# WebSocket 매니저 인스턴스
ws_manager = WebSocketManager()

# FastMCP 서버 인스턴스
mcp = FastMCP("Mempool WebSocket MCP Server")

@mcp.tool
async def subscribe_blocks() -> str:
    """블록 정보를 구독합니다."""
    try:
        await ws_manager.connect()
        client_id = str(uuid.uuid4())
        await ws_manager.subscribe_channel(client_id, ChannelType.BLOCKS)
        
        # 최근 메시지들을 가져와서 반환
        messages = []
        try:
            # 큐에서 최대 5개 메시지 수집 (타임아웃 5초)
            for _ in range(5):
                message = await asyncio.wait_for(ws_manager.message_queue.get(), timeout=1.0)
                if _is_block_message(message):
                    messages.append(message)
        except asyncio.TimeoutError:
            pass
        
        result = {
            "status": "subscribed",
            "channel": ChannelType.BLOCKS,
            "client_id": client_id,
            "recent_messages": messages
        }
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error("Failed to subscribe to blocks", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def subscribe_mempool_blocks() -> str:
    """멤풀 블록 정보를 구독합니다."""
    try:
        await ws_manager.connect()
        client_id = str(uuid.uuid4())
        await ws_manager.subscribe_channel(client_id, ChannelType.MEMPOOL_BLOCKS)
        
        messages = []
        try:
            for _ in range(5):
                message = await asyncio.wait_for(ws_manager.message_queue.get(), timeout=1.0)
                if _is_mempool_block_message(message):
                    messages.append(message)
        except asyncio.TimeoutError:
            pass
        
        result = {
            "status": "subscribed",
            "channel": ChannelType.MEMPOOL_BLOCKS,
            "client_id": client_id,
            "recent_messages": messages
        }
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error("Failed to subscribe to mempool blocks", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def subscribe_stats() -> str:
    """통계 정보를 구독합니다."""
    try:
        await ws_manager.connect()
        client_id = str(uuid.uuid4())
        await ws_manager.subscribe_channel(client_id, ChannelType.STATS)
        
        messages = []
        try:
            for _ in range(3):
                message = await asyncio.wait_for(ws_manager.message_queue.get(), timeout=1.0)
                if _is_stats_message(message):
                    messages.append(message)
        except asyncio.TimeoutError:
            pass
        
        result = {
            "status": "subscribed",
            "channel": ChannelType.STATS,
            "client_id": client_id,
            "recent_messages": messages
        }
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error("Failed to subscribe to stats", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def subscribe_live_chart() -> str:
    """실시간 2시간 차트 데이터를 구독합니다."""
    try:
        await ws_manager.connect()
        client_id = str(uuid.uuid4())
        await ws_manager.subscribe_channel(client_id, ChannelType.LIVE_2H_CHART)
        
        messages = []
        try:
            for _ in range(3):
                message = await asyncio.wait_for(ws_manager.message_queue.get(), timeout=1.0)
                if _is_chart_message(message):
                    messages.append(message)
        except asyncio.TimeoutError:
            pass
        
        result = {
            "status": "subscribed",
            "channel": ChannelType.LIVE_2H_CHART,
            "client_id": client_id,
            "recent_messages": messages
        }
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error("Failed to subscribe to live chart", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def track_address(address: str) -> str:
    """특정 비트코인 주소를 추적합니다."""
    try:
        await ws_manager.connect()
        client_id = str(uuid.uuid4())
        await ws_manager.track_address(client_id, address)
        
        result = {
            "status": "tracking",
            "address": address,
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error("Failed to track address", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def get_connection_status() -> str:
    """WebSocket 연결 상태를 확인합니다."""
    try:
        status = await ws_manager.get_connection_status()
        return json.dumps(status, indent=2)
    except Exception as e:
        logger.error("Failed to get connection status", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def unsubscribe_client(client_id: str) -> str:
    """클라이언트의 모든 구독을 해제합니다."""
    try:
        await ws_manager.unsubscribe_client(client_id)
        result = {
            "status": "unsubscribed",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Failed to unsubscribe client", error=str(e))
        return json.dumps({"error": str(e)})


# 헬퍼 함수들
def _is_block_message(message: Dict[str, Any]) -> bool:
    """블록 메시지인지 확인."""
    return "block" in message or "height" in message

def _is_mempool_block_message(message: Dict[str, Any]) -> bool:
    """멤풀 블록 메시지인지 확인."""
    return "mempool-blocks" in str(message) or "nTx" in message

def _is_stats_message(message: Dict[str, Any]) -> bool:
    """통계 메시지인지 확인."""
    return "mempool" in message and "vsize" in str(message)

def _is_chart_message(message: Dict[str, Any]) -> bool:
    """차트 메시지인지 확인."""
    return "live" in str(message) or "chart" in str(message)


# ========================================
# REST API 도구들  
# ========================================

@mcp.tool
async def get_address_info(address: str) -> str:
    """주소 정보를 조회합니다 (잔액, 거래 수 등)."""
    try:
        result = await rest_client.get_address(address)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Failed to get address info", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def get_address_balance(address: str) -> str:
    """주소의 잔액을 조회합니다."""
    try:
        result = await rest_client.get_address(address)
        balance_info = {
            "address": address,
            "balance": {
                "confirmed": result.get("chain_stats", {}).get("funded_txo_sum", 0) - result.get("chain_stats", {}).get("spent_txo_sum", 0),
                "unconfirmed": result.get("mempool_stats", {}).get("funded_txo_sum", 0) - result.get("mempool_stats", {}).get("spent_txo_sum", 0),
                "total": (result.get("chain_stats", {}).get("funded_txo_sum", 0) - result.get("chain_stats", {}).get("spent_txo_sum", 0)) + 
                        (result.get("mempool_stats", {}).get("funded_txo_sum", 0) - result.get("mempool_stats", {}).get("spent_txo_sum", 0))
            },
            "transactions": {
                "confirmed": result.get("chain_stats", {}).get("tx_count", 0),
                "unconfirmed": result.get("mempool_stats", {}).get("tx_count", 0)
            }
        }
        return json.dumps(balance_info, indent=2)
    except Exception as e:
        logger.error("Failed to get address balance", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def get_address_utxos(address: str) -> str:
    """주소의 UTXO 목록을 조회합니다."""
    try:
        result = await rest_client.get_address_utxo(address)
        utxo_info = {
            "address": address,
            "utxo_count": len(result),
            "total_value": sum(utxo.get("value", 0) for utxo in result),
            "utxos": result
        }
        return json.dumps(utxo_info, indent=2)
    except Exception as e:
        logger.error("Failed to get address UTXOs", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def get_address_transactions(address: str, after_txid: str = None) -> str:
    """주소의 거래 내역을 조회합니다."""
    try:
        result = await rest_client.get_address_txs(address, after_txid)
        tx_info = {
            "address": address,
            "transaction_count": len(result),
            "transactions": result
        }
        return json.dumps(tx_info, indent=2)
    except Exception as e:
        logger.error("Failed to get address transactions", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def get_recommended_fees() -> str:
    """추천 수수료를 조회합니다."""
    try:
        result = await rest_client.get_fees_recommended()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Failed to get recommended fees", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def get_mempool_info() -> str:
    """멤풀 정보를 조회합니다."""
    try:
        result = await rest_client.get_mempool()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Failed to get mempool info", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def get_transaction_info(txid: str) -> str:
    """거래 정보를 조회합니다."""
    try:
        result = await rest_client.get_tx(txid)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Failed to get transaction info", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def get_block_info(hash_or_height: str) -> str:
    """블록 정보를 조회합니다."""
    try:
        result = await rest_client.get_block(hash_or_height)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Failed to get block info", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def get_block_height() -> str:
    """현재 블록 높이를 조회합니다."""
    try:
        result = await rest_client.get_blocks_tip_height()
        return json.dumps({"current_height": result}, indent=2)
    except Exception as e:
        logger.error("Failed to get block height", error=str(e))
        return json.dumps({"error": str(e)})

@mcp.tool
async def validate_bitcoin_address(address: str) -> str:
    """비트코인 주소가 유효한지 검증합니다."""
    try:
        result = await rest_client.validate_address(address)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Failed to validate address", error=str(e))
        return json.dumps({"error": str(e)})


async def initialize_websocket():
    """WebSocket 초기화."""
    try:
        await ws_manager.connect()
        logger.info("WebSocket manager initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize WebSocket manager", error=str(e))
        raise


def create_mcp_server() -> FastMCP:
    """MCP 서버 인스턴스를 반환합니다."""
    # CORS 설정을 위한 옵션 추가
    if hasattr(mcp, 'configure'):
        # FastMCP에 CORS 설정이 있다면 적용
        mcp.configure(
            cors=True,
            cors_origins=["*"],
            cors_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            cors_headers=["*"]
        )
    
    return mcp 
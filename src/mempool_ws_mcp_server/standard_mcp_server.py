"""표준 MCP 라이브러리를 사용한 Mempool WebSocket MCP 서버 - Claude Desktop 호환."""

import asyncio
import json
import sys
import uuid
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Sequence

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions, ServerCapabilities
from mcp.types import (
    Tool,
    TextContent,
    GetPromptResult,
    Prompt,
    PromptArgument,
    GetResourceResult,
    Resource,
    ResourceContents,
    ResourceTemplate,
    CallToolResult,
    ListResourcesResult,
    ListPromptsResult,
    ListToolsResult,
)

from .websocket_manager import WebSocketManager
from .rest_client import rest_client
from .config import config
from .types import ChannelType

# 로깅 설정
logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# WebSocket 매니저 인스턴스
ws_manager = WebSocketManager()


class MempoolMCPServer:
    """Mempool WebSocket MCP 서버 클래스"""
    
    def __init__(self):
        self.server = Server("mempool-ws-mcp-server")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """핸들러 설정"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """사용 가능한 도구 목록 반환"""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="subscribe_blocks",
                        description="블록 정보를 구독합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="subscribe_mempool_blocks",
                        description="멤풀 블록 정보를 구독합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="subscribe_stats",
                        description="통계 정보를 구독합니다.",
                        inputSchema={
                            "type": "object", 
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="subscribe_live_chart",
                        description="실시간 2시간 차트 데이터를 구독합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="track_address",
                        description="특정 비트코인 주소를 추적합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "address": {
                                    "type": "string",
                                    "description": "추적할 비트코인 주소"
                                }
                            },
                            "required": ["address"]
                        }
                    ),
                    Tool(
                        name="get_connection_status",
                        description="WebSocket 연결 상태를 확인합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="unsubscribe_client",
                        description="클라이언트의 모든 구독을 해제합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "client_id": {
                                    "type": "string",
                                    "description": "구독 해제할 클라이언트 ID"
                                }
                            },
                            "required": ["client_id"]
                        }
                    ),
                    Tool(
                        name="get_address_info",
                        description="주소 정보를 조회합니다 (잔액, 거래 수 등).",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "address": {
                                    "type": "string",
                                    "description": "조회할 비트코인 주소"
                                }
                            },
                            "required": ["address"]
                        }
                    ),
                    Tool(
                        name="get_address_balance",
                        description="주소의 잔액을 조회합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "address": {
                                    "type": "string",
                                    "description": "조회할 비트코인 주소"
                                }
                            },
                            "required": ["address"]
                        }
                    ),
                    Tool(
                        name="get_address_utxos",
                        description="주소의 UTXO 목록을 조회합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "address": {
                                    "type": "string",
                                    "description": "조회할 비트코인 주소"
                                }
                            },
                            "required": ["address"]
                        }
                    ),
                    Tool(
                        name="get_address_transactions",
                        description="주소의 거래 내역을 조회합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "address": {
                                    "type": "string",
                                    "description": "조회할 비트코인 주소"
                                },
                                "after_txid": {
                                    "type": "string",
                                    "description": "이 트랜잭션 ID 이후의 거래들을 조회 (선택사항)",
                                    "default": None
                                }
                            },
                            "required": ["address"]
                        }
                    ),
                    Tool(
                        name="get_recommended_fees",
                        description="추천 수수료를 조회합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="get_mempool_info",
                        description="멤풀 정보를 조회합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="get_transaction_info",
                        description="거래 정보를 조회합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "txid": {
                                    "type": "string",
                                    "description": "조회할 거래 ID"
                                }
                            },
                            "required": ["txid"]
                        }
                    ),
                    Tool(
                        name="get_block_info",
                        description="블록 정보를 조회합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "hash_or_height": {
                                    "type": "string",
                                    "description": "블록 해시 또는 높이"
                                }
                            },
                            "required": ["hash_or_height"]
                        }
                    ),
                    Tool(
                        name="get_block_height",
                        description="현재 블록 높이를 조회합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="validate_bitcoin_address",
                        description="비트코인 주소가 유효한지 검증합니다.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "address": {
                                    "type": "string",
                                    "description": "검증할 비트코인 주소"
                                }
                            },
                            "required": ["address"]
                        }
                    )
                ]
            )

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """도구 호출 처리"""
            try:
                # WebSocket 연결 확인 및 초기화
                if not hasattr(ws_manager, '_ws') or ws_manager._ws is None:
                    await ws_manager.connect()
                
                if name == "subscribe_blocks":
                    result = await self._subscribe_blocks()
                elif name == "subscribe_mempool_blocks":
                    result = await self._subscribe_mempool_blocks()
                elif name == "subscribe_stats":
                    result = await self._subscribe_stats()
                elif name == "subscribe_live_chart":
                    result = await self._subscribe_live_chart()
                elif name == "track_address":
                    result = await self._track_address(arguments["address"])
                elif name == "get_connection_status":
                    result = await self._get_connection_status()
                elif name == "unsubscribe_client":
                    result = await self._unsubscribe_client(arguments["client_id"])
                elif name == "get_address_info":
                    result = await self._get_address_info(arguments["address"])
                elif name == "get_address_balance":
                    result = await self._get_address_balance(arguments["address"])
                elif name == "get_address_utxos":
                    result = await self._get_address_utxos(arguments["address"])
                elif name == "get_address_transactions":
                    result = await self._get_address_transactions(
                        arguments["address"], 
                        arguments.get("after_txid")
                    )
                elif name == "get_recommended_fees":
                    result = await self._get_recommended_fees()
                elif name == "get_mempool_info":
                    result = await self._get_mempool_info()
                elif name == "get_transaction_info":
                    result = await self._get_transaction_info(arguments["txid"])
                elif name == "get_block_info":
                    result = await self._get_block_info(arguments["hash_or_height"])
                elif name == "get_block_height":
                    result = await self._get_block_height()
                elif name == "validate_bitcoin_address":
                    result = await self._validate_bitcoin_address(arguments["address"])
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return CallToolResult(
                    content=[TextContent(type="text", text=result)]
                )
                
            except Exception as e:
                logger.error(f"Tool {name} failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({"error": str(e)}))]
                )

    # WebSocket 관련 메서드들
    async def _subscribe_blocks(self) -> str:
        """블록 정보를 구독합니다."""
        try:
            await ws_manager.connect()
            client_id = str(uuid.uuid4())
            await ws_manager.subscribe_channel(client_id, ChannelType.BLOCKS)
            
            # 최근 메시지들을 가져와서 반환
            messages = []
            try:
                for _ in range(5):
                    message = await asyncio.wait_for(ws_manager.message_queue.get(), timeout=1.0)
                    if self._is_block_message(message):
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

    async def _subscribe_mempool_blocks(self) -> str:
        """멤풀 블록 정보를 구독합니다."""
        try:
            await ws_manager.connect()
            client_id = str(uuid.uuid4())
            await ws_manager.subscribe_channel(client_id, ChannelType.MEMPOOL_BLOCKS)
            
            messages = []
            try:
                for _ in range(5):
                    message = await asyncio.wait_for(ws_manager.message_queue.get(), timeout=1.0)
                    if self._is_mempool_block_message(message):
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

    async def _subscribe_stats(self) -> str:
        """통계 정보를 구독합니다."""
        try:
            await ws_manager.connect()
            client_id = str(uuid.uuid4())
            await ws_manager.subscribe_channel(client_id, ChannelType.STATS)
            
            messages = []
            try:
                for _ in range(3):
                    message = await asyncio.wait_for(ws_manager.message_queue.get(), timeout=1.0)
                    if self._is_stats_message(message):
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

    async def _subscribe_live_chart(self) -> str:
        """실시간 2시간 차트 데이터를 구독합니다."""
        try:
            await ws_manager.connect()
            client_id = str(uuid.uuid4())
            await ws_manager.subscribe_channel(client_id, ChannelType.LIVE_2H_CHART)
            
            messages = []
            try:
                for _ in range(3):
                    message = await asyncio.wait_for(ws_manager.message_queue.get(), timeout=1.0)
                    if self._is_chart_message(message):
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

    async def _track_address(self, address: str) -> str:
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

    async def _get_connection_status(self) -> str:
        """WebSocket 연결 상태를 확인합니다."""
        try:
            status = await ws_manager.get_connection_status()
            return json.dumps(status, indent=2)
        except Exception as e:
            logger.error("Failed to get connection status", error=str(e))
            return json.dumps({"error": str(e)})

    async def _unsubscribe_client(self, client_id: str) -> str:
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

    # REST API 관련 메서드들
    async def _get_address_info(self, address: str) -> str:
        """주소 정보를 조회합니다."""
        try:
            info = await rest_client.get_address_info(address)
            return json.dumps(info, indent=2)
        except Exception as e:
            logger.error("Failed to get address info", error=str(e))
            return json.dumps({"error": str(e)})

    async def _get_address_balance(self, address: str) -> str:
        """주소의 잔액을 조회합니다."""
        try:
            balance = await rest_client.get_address_balance(address)
            return json.dumps(balance, indent=2)
        except Exception as e:
            logger.error("Failed to get address balance", error=str(e))
            return json.dumps({"error": str(e)})

    async def _get_address_utxos(self, address: str) -> str:
        """주소의 UTXO 목록을 조회합니다."""
        try:
            utxos = await rest_client.get_address_utxos(address)
            return json.dumps(utxos, indent=2)
        except Exception as e:
            logger.error("Failed to get address UTXOs", error=str(e))
            return json.dumps({"error": str(e)})

    async def _get_address_transactions(self, address: str, after_txid: Optional[str] = None) -> str:
        """주소의 거래 내역을 조회합니다."""
        try:
            transactions = await rest_client.get_address_transactions(address, after_txid)
            return json.dumps(transactions, indent=2)
        except Exception as e:
            logger.error("Failed to get address transactions", error=str(e))
            return json.dumps({"error": str(e)})

    async def _get_recommended_fees(self) -> str:
        """추천 수수료를 조회합니다."""
        try:
            fees = await rest_client.get_recommended_fees()
            return json.dumps(fees, indent=2)
        except Exception as e:
            logger.error("Failed to get recommended fees", error=str(e))
            return json.dumps({"error": str(e)})

    async def _get_mempool_info(self) -> str:
        """멤풀 정보를 조회합니다."""
        try:
            info = await rest_client.get_mempool_info()
            return json.dumps(info, indent=2)
        except Exception as e:
            logger.error("Failed to get mempool info", error=str(e))
            return json.dumps({"error": str(e)})

    async def _get_transaction_info(self, txid: str) -> str:
        """거래 정보를 조회합니다."""
        try:
            info = await rest_client.get_transaction_info(txid)
            return json.dumps(info, indent=2)
        except Exception as e:
            logger.error("Failed to get transaction info", error=str(e))
            return json.dumps({"error": str(e)})

    async def _get_block_info(self, hash_or_height: str) -> str:
        """블록 정보를 조회합니다."""
        try:
            info = await rest_client.get_block_info(hash_or_height)
            return json.dumps(info, indent=2)
        except Exception as e:
            logger.error("Failed to get block info", error=str(e))
            return json.dumps({"error": str(e)})

    async def _get_block_height(self) -> str:
        """현재 블록 높이를 조회합니다."""
        try:
            height = await rest_client.get_block_height()
            return json.dumps({"block_height": height}, indent=2)
        except Exception as e:
            logger.error("Failed to get block height", error=str(e))
            return json.dumps({"error": str(e)})

    async def _validate_bitcoin_address(self, address: str) -> str:
        """비트코인 주소가 유효한지 검증합니다."""
        try:
            is_valid = await rest_client.validate_bitcoin_address(address)
            return json.dumps({"address": address, "is_valid": is_valid}, indent=2)
        except Exception as e:
            logger.error("Failed to validate bitcoin address", error=str(e))
            return json.dumps({"error": str(e)})

    # 헬퍼 메서드들
    def _is_block_message(self, message: Dict[str, Any]) -> bool:
        """블록 메시지인지 확인."""
        return "block" in message or "height" in message

    def _is_mempool_block_message(self, message: Dict[str, Any]) -> bool:
        """멤풀 블록 메시지인지 확인."""
        return "mempool-blocks" in str(message) or "nTx" in message

    def _is_stats_message(self, message: Dict[str, Any]) -> bool:
        """통계 메시지인지 확인."""
        return "mempool" in message and "vsize" in str(message)

    def _is_chart_message(self, message: Dict[str, Any]) -> bool:
        """차트 메시지인지 확인."""
        return "chart" in str(message) or "prices" in str(message)

    async def run(self):
        """서버 실행"""
        # WebSocket 초기화
        try:
            await ws_manager.connect()
            logger.info("WebSocket connection established")
        except Exception as e:
            logger.error("Failed to initialize WebSocket", error=str(e))
        
        # STDIO 서버 실행
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mempool-ws-mcp-server",
                    server_version="1.0.0",
                    capabilities=ServerCapabilities(
                        tools={},
                        resources={},
                        prompts={}
                    )
                )
            )


def main():
    """메인 함수 - 표준 MCP 서버를 STDIO 모드로 실행"""
    try:
        server = MempoolMCPServer()
        logger.info("Starting standard MCP server in STDIO mode")
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Server startup failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main() 
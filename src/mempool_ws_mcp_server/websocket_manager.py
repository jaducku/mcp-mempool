"""WebSocket 연결 관리자."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import structlog
import websockets
from websockets.exceptions import ConnectionClosed
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import config
from .types import ChannelType, WebSocketMessage, TrackAddressMessage


logger = structlog.get_logger(__name__)


class WebSocketManager:
    """Mempool WebSocket 연결 관리자."""

    def __init__(self, ws_url: str = None) -> None:
        """초기화."""
        self.ws_url = ws_url or config.MEMPOOL_WS_URL
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.subscriptions: Dict[str, Set[str]] = {}  # client_id -> channels
        self.channel_subscribers: Dict[str, Set[str]] = {}  # channel -> client_ids
        self.message_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(
            maxsize=config.MAX_MESSAGE_QUEUE_SIZE
        )
        self.connection_lock = asyncio.Lock()
        self.is_connected = False
        self.last_ping = time.time()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.WS_MAX_RECONNECT_ATTEMPTS
        self._listeners: Dict[str, List[asyncio.Queue[Dict[str, Any]]]] = {}

    async def connect(self) -> None:
        """WebSocket 연결 설정."""
        async with self.connection_lock:
            if self.is_connected and self.websocket:
                logger.info("Already connected to WebSocket")
                return

            try:
                logger.info("Connecting to WebSocket", url=self.ws_url)
                self.websocket = await websockets.connect(
                    self.ws_url,
                    ping_interval=config.WS_PING_INTERVAL,
                    ping_timeout=config.WS_PING_TIMEOUT,
                    close_timeout=10,
                )
                self.is_connected = True
                self.reconnect_attempts = 0
                logger.info("Successfully connected to WebSocket")

                # 백그라운드 태스크 시작
                asyncio.create_task(self._message_handler())
                asyncio.create_task(self._heartbeat())

            except Exception as e:
                logger.error("Failed to connect to WebSocket", error=str(e))
                self.is_connected = False
                raise

    async def disconnect(self) -> None:
        """WebSocket 연결 해제."""
        async with self.connection_lock:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            self.is_connected = False
            logger.info("Disconnected from WebSocket")

    @retry(
        retry=retry_if_exception_type(ConnectionClosed),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def _send_message(self, message: Dict[str, Any]) -> None:
        """메시지 전송."""
        if not self.websocket or not self.is_connected:
            await self.connect()

        try:
            await self.websocket.send(json.dumps(message))
            logger.debug("Sent message", message=message)
        except ConnectionClosed:
            logger.warning("WebSocket connection closed, attempting to reconnect")
            self.is_connected = False
            raise

    async def subscribe_channel(self, client_id: str, channel: str) -> None:
        """채널 구독."""
        logger.info("Subscribing to channel", client_id=client_id, channel=channel)

        # 클라이언트 구독 정보 업데이트
        if client_id not in self.subscriptions:
            self.subscriptions[client_id] = set()
        self.subscriptions[client_id].add(channel)

        # 채널 구독자 정보 업데이트
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()
        self.channel_subscribers[channel].add(client_id)

        # 새 채널인 경우 WebSocket에 구독 요청
        if len(self.channel_subscribers[channel]) == 1:
            if channel == ChannelType.TRACK_ADDRESS:
                # 주소 추적은 별도 처리
                return
            
            message = WebSocketMessage(action="want", data=[channel])
            await self._send_message(message.model_dump())

    async def unsubscribe_channel(self, client_id: str, channel: str) -> None:
        """채널 구독 해제."""
        logger.info("Unsubscribing from channel", client_id=client_id, channel=channel)

        # 클라이언트 구독 정보 업데이트
        if client_id in self.subscriptions:
            self.subscriptions[client_id].discard(channel)
            if not self.subscriptions[client_id]:
                del self.subscriptions[client_id]

        # 채널 구독자 정보 업데이트
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(client_id)
            if not self.channel_subscribers[channel]:
                del self.channel_subscribers[channel]
                # 구독자가 없으면 WebSocket에서 구독 해제
                if channel != ChannelType.TRACK_ADDRESS:
                    message = WebSocketMessage(action="want", data=[])
                    await self._send_message(message.model_dump())

    async def track_address(self, client_id: str, address: str) -> None:
        """주소 추적."""
        logger.info("Tracking address", client_id=client_id, address=address)
        
        message = TrackAddressMessage(track_address=address)
        await self._send_message(message.model_dump())
        
        # 클라이언트 구독 정보에 추가
        await self.subscribe_channel(client_id, f"track-address:{address}")

    async def unsubscribe_client(self, client_id: str) -> None:
        """클라이언트의 모든 구독 해제."""
        logger.info("Unsubscribing client", client_id=client_id)
        
        if client_id in self.subscriptions:
            channels = list(self.subscriptions[client_id])
            for channel in channels:
                await self.unsubscribe_channel(client_id, channel)

    async def add_listener(self, channel: str, queue: asyncio.Queue[Dict[str, Any]]) -> None:
        """채널 리스너 추가."""
        if channel not in self._listeners:
            self._listeners[channel] = []
        self._listeners[channel].append(queue)

    async def remove_listener(self, channel: str, queue: asyncio.Queue[Dict[str, Any]]) -> None:
        """채널 리스너 제거."""
        if channel in self._listeners:
            try:
                self._listeners[channel].remove(queue)
                if not self._listeners[channel]:
                    del self._listeners[channel]
            except ValueError:
                pass

    async def _message_handler(self) -> None:
        """메시지 핸들러."""
        while self.is_connected:
            try:
                if not self.websocket:
                    await asyncio.sleep(1)
                    continue

                message = await self.websocket.recv()
                data = json.loads(message)
                
                logger.debug("Received message", data=data)
                
                # 메시지를 큐에 추가
                await self.message_queue.put(data)
                
                # 리스너들에게 메시지 전달
                await self._distribute_message(data)

            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self.is_connected = False
                await self._handle_reconnect()
                break
            except json.JSONDecodeError as e:
                logger.error("Failed to decode message", error=str(e))
            except Exception as e:
                logger.error("Unexpected error in message handler", error=str(e))

    async def _distribute_message(self, data: Dict[str, Any]) -> None:
        """메시지를 리스너들에게 배포."""
        # 메시지 타입에 따라 적절한 채널 결정
        channel = self._determine_channel(data)
        
        if channel and channel in self._listeners:
            for queue in self._listeners[channel]:
                try:
                    await queue.put(data)
                except asyncio.QueueFull:
                    logger.warning("Queue full, dropping message", channel=channel)

    def _determine_channel(self, data: Dict[str, Any]) -> Optional[str]:
        """메시지 데이터로부터 채널 결정."""
        # mempool.space WebSocket 메시지 구조에 따라 채널 결정
        if "block" in data:
            return ChannelType.BLOCKS
        elif "mempool-blocks" in data:
            return ChannelType.MEMPOOL_BLOCKS
        elif "mempoolInfo" in data:
            return ChannelType.STATS
        elif "live-2h-chart" in data:
            return ChannelType.LIVE_2H
        elif "address" in data:
            return ChannelType.TRACK_ADDRESS
        
        return None

    async def _heartbeat(self) -> None:
        """하트비트 관리."""
        while self.is_connected:
            try:
                if self.websocket:
                    await self.websocket.ping()
                    self.last_ping = time.time()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error("Heartbeat failed", error=str(e))
                self.is_connected = False
                break

    async def _handle_reconnect(self) -> None:
        """재연결 처리."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return

        self.reconnect_attempts += 1
        backoff = min(2 ** self.reconnect_attempts, 60)
        
        logger.info(
            "Attempting to reconnect",
            attempt=self.reconnect_attempts,
            backoff=backoff,
        )
        
        await asyncio.sleep(backoff)
        
        try:
            await self.connect()
            
            # 기존 구독 복원
            await self._restore_subscriptions()
            
        except Exception as e:
            logger.error("Reconnection failed", error=str(e))
            await self._handle_reconnect()

    async def _restore_subscriptions(self) -> None:
        """구독 복원."""
        logger.info("Restoring subscriptions")
        
        # 모든 활성 채널을 다시 구독
        for channel in self.channel_subscribers:
            if channel.startswith("track-address:"):
                address = channel.split(":", 1)[1]
                message = TrackAddressMessage(track_address=address)
                await self._send_message(message.model_dump())
            else:
                message = WebSocketMessage(action="want", data=[channel])
                await self._send_message(message.model_dump())

    async def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 반환."""
        return {
            "connected": self.is_connected,
            "last_ping": self.last_ping,
            "reconnect_attempts": self.reconnect_attempts,
            "active_subscriptions": len(self.channel_subscribers),
            "total_clients": len(self.subscriptions),
        } 
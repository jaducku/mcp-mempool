"""WebSocket 매니저 테스트."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mempool_ws_mcp_server.websocket_manager import WebSocketManager
from mempool_ws_mcp_server.types import ChannelType


@pytest.fixture
async def ws_manager():
    """WebSocket 매니저 픽스처."""
    manager = WebSocketManager("wss://test.example.com/ws")
    yield manager
    # 정리
    if manager.websocket:
        await manager.disconnect()


@pytest.mark.asyncio
class TestWebSocketManager:
    """WebSocket 매니저 테스트 클래스."""

    async def test_initial_state(self, ws_manager):
        """초기 상태 테스트."""
        assert not ws_manager.is_connected
        assert ws_manager.websocket is None
        assert len(ws_manager.subscriptions) == 0
        assert len(ws_manager.channel_subscribers) == 0

    @patch('mempool_ws_mcp_server.websocket_manager.websockets.connect')
    async def test_connect_success(self, mock_connect, ws_manager):
        """연결 성공 테스트."""
        mock_websocket = AsyncMock()
        mock_connect.return_value = mock_websocket
        
        await ws_manager.connect()
        
        assert ws_manager.is_connected
        assert ws_manager.websocket == mock_websocket
        mock_connect.assert_called_once()

    @patch('mempool_ws_mcp_server.websocket_manager.websockets.connect')
    async def test_connect_failure(self, mock_connect, ws_manager):
        """연결 실패 테스트."""
        mock_connect.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await ws_manager.connect()
        
        assert not ws_manager.is_connected
        assert ws_manager.websocket is None

    async def test_subscribe_channel(self, ws_manager):
        """채널 구독 테스트."""
        client_id = "test_client"
        channel = ChannelType.BLOCKS
        
        with patch.object(ws_manager, '_send_message', new_callable=AsyncMock) as mock_send:
            await ws_manager.subscribe_channel(client_id, channel)
        
        assert client_id in ws_manager.subscriptions
        assert channel in ws_manager.subscriptions[client_id]
        assert channel in ws_manager.channel_subscribers
        assert client_id in ws_manager.channel_subscribers[channel]

    async def test_unsubscribe_channel(self, ws_manager):
        """채널 구독 해제 테스트."""
        client_id = "test_client"
        channel = ChannelType.BLOCKS
        
        # 먼저 구독
        ws_manager.subscriptions[client_id] = {channel}
        ws_manager.channel_subscribers[channel] = {client_id}
        
        await ws_manager.unsubscribe_channel(client_id, channel)
        
        assert client_id not in ws_manager.subscriptions
        assert channel not in ws_manager.channel_subscribers

    async def test_track_address(self, ws_manager):
        """주소 추적 테스트."""
        client_id = "test_client"
        address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        
        with patch.object(ws_manager, '_send_message', new_callable=AsyncMock) as mock_send:
            await ws_manager.track_address(client_id, address)
        
        expected_channel = f"track-address:{address}"
        assert client_id in ws_manager.subscriptions
        assert expected_channel in ws_manager.subscriptions[client_id]

    async def test_unsubscribe_client(self, ws_manager):
        """클라이언트 구독 해제 테스트."""
        client_id = "test_client"
        channels = [ChannelType.BLOCKS, ChannelType.STATS]
        
        # 구독 설정
        ws_manager.subscriptions[client_id] = set(channels)
        for channel in channels:
            ws_manager.channel_subscribers[channel] = {client_id}
        
        await ws_manager.unsubscribe_client(client_id)
        
        assert client_id not in ws_manager.subscriptions
        for channel in channels:
            assert channel not in ws_manager.channel_subscribers

    async def test_determine_channel(self, ws_manager):
        """채널 결정 테스트."""
        # 블록 메시지
        block_message = {"block": {"height": 123456}}
        assert ws_manager._determine_channel(block_message) == ChannelType.BLOCKS
        
        # 통계 메시지
        stats_message = {"mempoolInfo": {"count": 1000}}
        assert ws_manager._determine_channel(stats_message) == ChannelType.STATS
        
        # 알 수 없는 메시지
        unknown_message = {"unknown": "data"}
        assert ws_manager._determine_channel(unknown_message) is None

    async def test_get_connection_status(self, ws_manager):
        """연결 상태 조회 테스트."""
        status = await ws_manager.get_connection_status()
        
        assert "connected" in status
        assert "last_ping" in status
        assert "reconnect_attempts" in status
        assert "active_subscriptions" in status
        assert "total_clients" in status
        
        assert status["connected"] is False
        assert status["active_subscriptions"] == 0
        assert status["total_clients"] == 0

    async def test_add_remove_listener(self, ws_manager):
        """리스너 추가/제거 테스트."""
        channel = ChannelType.BLOCKS
        queue = asyncio.Queue()
        
        # 리스너 추가
        await ws_manager.add_listener(channel, queue)
        assert channel in ws_manager._listeners
        assert queue in ws_manager._listeners[channel]
        
        # 리스너 제거
        await ws_manager.remove_listener(channel, queue)
        assert channel not in ws_manager._listeners

    @patch('mempool_ws_mcp_server.websocket_manager.websockets.connect')
    async def test_message_distribution(self, mock_connect, ws_manager):
        """메시지 배포 테스트."""
        mock_websocket = AsyncMock()
        mock_connect.return_value = mock_websocket
        
        # 연결
        await ws_manager.connect()
        
        # 리스너 설정
        channel = ChannelType.BLOCKS
        queue = asyncio.Queue()
        await ws_manager.add_listener(channel, queue)
        
        # 메시지 배포
        test_message = {"block": {"height": 123456}}
        await ws_manager._distribute_message(test_message)
        
        # 큐에서 메시지 확인
        received_message = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received_message == test_message


@pytest.mark.asyncio 
async def test_websocket_manager_integration():
    """WebSocket 매니저 통합 테스트."""
    with patch('mempool_ws_mcp_server.websocket_manager.websockets.connect') as mock_connect:
        mock_websocket = AsyncMock()
        mock_connect.return_value = mock_websocket
        
        manager = WebSocketManager("wss://test.example.com/ws")
        
        try:
            # 연결
            await manager.connect()
            assert manager.is_connected
            
            # 채널 구독
            client_id = "integration_test_client"
            await manager.subscribe_channel(client_id, ChannelType.BLOCKS)
            
            # 상태 확인
            status = await manager.get_connection_status()
            assert status["connected"]
            assert status["active_subscriptions"] == 1
            assert status["total_clients"] == 1
            
        finally:
            await manager.disconnect() 
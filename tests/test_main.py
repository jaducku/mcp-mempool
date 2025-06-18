"""메인 서버 테스트."""

import asyncio
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from mempool_ws_mcp_server.main import app


@pytest.fixture
async def client():
    """테스트 클라이언트 픽스처."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestMainEndpoints:
    """메인 엔드포인트 테스트."""

    async def test_root_endpoint(self, client):
        """루트 엔드포인트 테스트."""
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Mempool WebSocket MCP Server"
        assert data["version"] == "0.1.0"
        assert "endpoints" in data
        assert "health" in data["endpoints"]
        assert "sse" in data["endpoints"]

    async def test_health_endpoint_healthy(self, client):
        """헬스 체크 엔드포인트 테스트 - 정상 상태."""
        with patch('mempool_ws_mcp_server.main.ws_manager') as mock_ws_manager:
            mock_ws_manager.get_connection_status.return_value = {
                "connected": True,
                "active_subscriptions": 2,
                "total_clients": 1,
                "last_ping": 1234567890,
                "reconnect_attempts": 0
            }
            
            response = await client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["websocket_connected"] is True
            assert data["active_subscriptions"] == 2
            assert data["total_clients"] == 1

    async def test_health_endpoint_unhealthy(self, client):
        """헬스 체크 엔드포인트 테스트 - 비정상 상태."""
        with patch('mempool_ws_mcp_server.main.ws_manager') as mock_ws_manager:
            mock_ws_manager.get_connection_status.return_value = {
                "connected": False,
                "active_subscriptions": 0,
                "total_clients": 0,
                "last_ping": 1234567890,
                "reconnect_attempts": 3
            }
            
            response = await client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["websocket_connected"] is False

    async def test_health_endpoint_error(self, client):
        """헬스 체크 엔드포인트 테스트 - 에러 상태."""
        with patch('mempool_ws_mcp_server.main.ws_manager') as mock_ws_manager:
            mock_ws_manager.get_connection_status.side_effect = Exception("Connection error")
            
            response = await client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "error"
            assert "error" in data

    async def test_mcp_endpoint_success(self, client):
        """MCP 엔드포인트 테스트 - 성공."""
        with patch('mempool_ws_mcp_server.main.mcp') as mock_mcp:
            mock_mcp.handle_request.return_value = {"result": "success"}
            
            request_data = {"method": "list_tools", "params": {}}
            response = await client.post("/mcp", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "success"

    async def test_mcp_endpoint_error(self, client):
        """MCP 엔드포인트 테스트 - 에러."""
        with patch('mempool_ws_mcp_server.main.mcp') as mock_mcp:
            mock_mcp.handle_request.side_effect = Exception("MCP error")
            
            request_data = {"method": "list_tools", "params": {}}
            response = await client.post("/mcp", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == -1
            assert "MCP error" in data["error"]["message"]

    async def test_sse_endpoint_headers(self, client):
        """SSE 엔드포인트 헤더 테스트."""
        with patch('mempool_ws_mcp_server.main.ws_manager') as mock_ws_manager:
            mock_ws_manager.is_connected = False
            mock_ws_manager.connect = AsyncMock()
            mock_ws_manager.add_listener = AsyncMock()
            mock_ws_manager.remove_listener = AsyncMock()
            
            # SSE 스트림 시작하고 바로 종료 시뮬레이션
            async def mock_event_stream():
                yield "data: {\"type\": \"connection\", \"status\": \"connected\"}\n\n"
                return
            
            with patch('mempool_ws_mcp_server.main.app.get') as mock_get:
                # 실제 SSE 엔드포인트 대신 간단한 응답 반환
                response = await client.get("/sse")
                
                # 응답 헤더 확인
                assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
                assert "cache-control" in response.headers
                assert "connection" in response.headers


@pytest.mark.asyncio
async def test_server_startup_shutdown():
    """서버 시작/종료 테스트."""
    with patch('mempool_ws_mcp_server.main.initialize_websocket') as mock_init:
        with patch('mempool_ws_mcp_server.main.ws_manager') as mock_ws_manager:
            mock_init.return_value = None
            mock_ws_manager.disconnect.return_value = None
            
            # lifespan 컨텍스트 매니저 테스트
            from mempool_ws_mcp_server.main import lifespan
            
            async with lifespan(app):
                # 서버가 시작되었는지 확인
                mock_init.assert_called_once()
            
            # 서버가 종료되었는지 확인
            mock_ws_manager.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_server_startup_failure():
    """서버 시작 실패 테스트."""
    with patch('mempool_ws_mcp_server.main.initialize_websocket') as mock_init:
        mock_init.side_effect = Exception("Startup failed")
        
        from mempool_ws_mcp_server.main import lifespan
        
        with pytest.raises(Exception, match="Startup failed"):
            async with lifespan(app):
                pass


def test_signal_handlers():
    """시그널 핸들러 테스트."""
    with patch('signal.signal') as mock_signal:
        from mempool_ws_mcp_server.main import setup_signal_handlers
        
        setup_signal_handlers()
        
        # SIGINT와 SIGTERM 핸들러가 설정되었는지 확인
        assert mock_signal.call_count == 2


@pytest.mark.asyncio 
async def test_run_server_config():
    """서버 실행 설정 테스트."""
    with patch('mempool_ws_mcp_server.main.uvicorn.Server') as mock_server_class:
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default: {
                "HOST": "test_host",
                "PORT": "9999", 
                "LOG_LEVEL": "debug"
            }.get(key, default)
            
            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server
            
            from mempool_ws_mcp_server.main import run_server
            
            # 서버 실행 시뮬레이션 (바로 리턴)
            mock_server.serve.return_value = None
            
            await run_server()
            
            # 서버가 올바른 설정으로 생성되었는지 확인
            mock_server_class.assert_called_once()
            config = mock_server_class.call_args[0][0]
            assert config.host == "test_host"
            assert config.port == 9999
            assert config.log_level == "debug"


if __name__ == "__main__":
    pytest.main([__file__]) 
"""Mempool.space REST API 클라이언트."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union

import aiohttp
import structlog

from .config import config

logger = structlog.get_logger(__name__)


class MempoolRestClient:
    """Mempool.space REST API 클라이언트."""
    
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or config.MEMPOOL_API_URL).rstrip('/')
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP 세션을 가져옵니다."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=config.HTTP_TIMEOUT),
                headers={'User-Agent': 'MCP-Mempool-Client/1.0'}
            )
        return self._session
    
    async def close(self):
        """세션을 종료합니다."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """HTTP 요청을 보냅니다."""
        url = f"{self.base_url}{endpoint}"
        session = await self._get_session()
        
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error("HTTP request failed", url=url, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in HTTP request", url=url, error=str(e))
            raise
    
    # 주소 관련 API
    async def get_address(self, address: str) -> Dict[str, Any]:
        """주소 정보를 가져옵니다."""
        return await self._request(f"/address/{address}")
    
    async def get_address_txs(self, address: str, after_txid: Optional[str] = None) -> List[Dict[str, Any]]:
        """주소의 거래 내역을 가져옵니다."""
        params = {"after_txid": after_txid} if after_txid else None
        return await self._request(f"/address/{address}/txs", params=params)
    
    async def get_address_txs_chain(self, address: str, last_seen_txid: Optional[str] = None) -> List[Dict[str, Any]]:
        """주소의 확인된 거래 내역을 가져옵니다."""
        params = {"last_seen_txid": last_seen_txid} if last_seen_txid else None
        return await self._request(f"/address/{address}/txs/chain", params=params)
    
    async def get_address_txs_mempool(self, address: str) -> List[Dict[str, Any]]:
        """주소의 멤풀 거래 내역을 가져옵니다."""
        return await self._request(f"/address/{address}/txs/mempool")
    
    async def get_address_utxo(self, address: str) -> List[Dict[str, Any]]:
        """주소의 UTXO를 가져옵니다."""
        return await self._request(f"/address/{address}/utxo")
    
    # 블록 관련 API
    async def get_block(self, hash_or_height: Union[str, int]) -> Dict[str, Any]:
        """블록 정보를 가져옵니다."""
        return await self._request(f"/block/{hash_or_height}")
    
    async def get_block_status(self, hash: str) -> Dict[str, Any]:
        """블록 상태를 가져옵니다."""
        return await self._request(f"/block/{hash}/status")
    
    async def get_block_txs(self, hash: str, start_index: int = 0) -> List[Dict[str, Any]]:
        """블록의 거래 목록을 가져옵니다."""
        params = {"start_index": start_index} if start_index > 0 else None
        return await self._request(f"/block/{hash}/txs", params=params)
    
    async def get_block_txids(self, hash: str) -> List[str]:
        """블록의 거래 ID 목록을 가져옵니다."""
        return await self._request(f"/block/{hash}/txids")
    
    async def get_block_txid(self, hash: str, index: int) -> str:
        """블록의 특정 인덱스 거래 ID를 가져옵니다."""
        return await self._request(f"/block/{hash}/txid/{index}")
    
    async def get_block_raw(self, hash: str) -> str:
        """블록의 raw 데이터를 가져옵니다."""
        return await self._request(f"/block/{hash}/raw")
    
    async def get_blocks(self, start_height: Optional[int] = None) -> List[Dict[str, Any]]:
        """최근 블록 목록을 가져옵니다."""
        params = {"start_height": start_height} if start_height else None
        return await self._request("/blocks", params=params)
    
    async def get_blocks_tip_height(self) -> int:
        """최신 블록 높이를 가져옵니다."""
        return await self._request("/blocks/tip/height")
    
    async def get_blocks_tip_hash(self) -> str:
        """최신 블록 해시를 가져옵니다."""
        return await self._request("/blocks/tip/hash")
    
    # 거래 관련 API
    async def get_tx(self, txid: str) -> Dict[str, Any]:
        """거래 정보를 가져옵니다."""
        return await self._request(f"/tx/{txid}")
    
    async def get_tx_status(self, txid: str) -> Dict[str, Any]:
        """거래 상태를 가져옵니다."""
        return await self._request(f"/tx/{txid}/status")
    
    async def get_tx_hex(self, txid: str) -> str:
        """거래의 hex 데이터를 가져옵니다."""
        return await self._request(f"/tx/{txid}/hex")
    
    async def get_tx_raw(self, txid: str) -> str:
        """거래의 raw 데이터를 가져옵니다."""
        return await self._request(f"/tx/{txid}/raw")
    
    async def get_tx_merkleblock_proof(self, txid: str) -> str:
        """거래의 merkle block proof를 가져옵니다."""
        return await self._request(f"/tx/{txid}/merkleblock-proof")
    
    async def get_tx_merkle_proof(self, txid: str) -> Dict[str, Any]:
        """거래의 merkle proof를 가져옵니다."""
        return await self._request(f"/tx/{txid}/merkle-proof")
    
    async def get_tx_outspend(self, txid: str, vout: int) -> Dict[str, Any]:
        """거래 출력의 사용 정보를 가져옵니다."""
        return await self._request(f"/tx/{txid}/outspend/{vout}")
    
    async def get_tx_outspends(self, txid: str) -> List[Dict[str, Any]]:
        """거래 출력들의 사용 정보를 가져옵니다."""
        return await self._request(f"/tx/{txid}/outspends")
    
    async def post_tx(self, tx_hex: str) -> str:
        """거래를 브로드캐스트합니다."""
        session = await self._get_session()
        url = f"{self.base_url}/tx"
        
        try:
            async with session.post(url, data=tx_hex, headers={'Content-Type': 'text/plain'}) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            logger.error("Transaction broadcast failed", error=str(e))
            raise
    
    # 멤풀 관련 API
    async def get_mempool(self) -> Dict[str, Any]:
        """멤풀 정보를 가져옵니다."""
        return await self._request("/mempool")
    
    async def get_mempool_txids(self) -> List[str]:
        """멤풀의 거래 ID 목록을 가져옵니다."""
        return await self._request("/mempool/txids")
    
    async def get_mempool_recent(self) -> List[Dict[str, Any]]:
        """최근 멤풀 거래들을 가져옵니다.""" 
        return await self._request("/mempool/recent")
    
    # 수수료 관련 API
    async def get_fees_recommended(self) -> Dict[str, int]:
        """추천 수수료를 가져옵니다."""
        return await self._request("/v1/fees/recommended")
    
    async def get_fees_mempool_blocks(self) -> List[Dict[str, Any]]:
        """멤풀 블록별 수수료 정보를 가져옵니다."""
        return await self._request("/v1/fees/mempool-blocks")
    
    # 난이도 조정 API
    async def get_difficulty_adjustment(self) -> Dict[str, Any]:
        """난이도 조정 정보를 가져옵니다."""
        return await self._request("/v1/difficulty-adjustment")
    
    # 주소 접두사 검색 API
    async def validate_address(self, address: str) -> Dict[str, Any]:
        """주소가 유효한지 검증합니다."""
        return await self._request(f"/v1/validate-address/{address}")


# 글로벌 클라이언트 인스턴스
rest_client = MempoolRestClient() 
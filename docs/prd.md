Mempool WebSocket MCP 서버 PRD (Product Requirements Document)

1. 문서 정보
	•	작성일: 2025‑06‑18
	•	작성자: Sungji Kim & LLM 지원
	•	버전: v0.1 (Draft)

2. 개요 및 목적

Mempool.space WebSocket API에서 제공하는 실시간 비트코인 네트워크 데이터를 MCP(Model Context Protocol) 서버 형태로 래핑하여 사내 LLM Agent 및 외부 애플리케이션이 도구(tool) 형태로 쉽게 구독·활용할 수 있도록 한다. 목표는 다음과 같다.
	1.	FastMCP 2.0 프레임워크를 사용해 최소한의 코드로 고성능 MCP 서버 구현  citeturn7view0
	2.	mempool WebSocket 엔드포인트(wss://mempool.space/api/v1/ws)의 실시간 스트림을 blocks / mempool‑blocks / stats / live‑2h‑chart / track‑address 채널별로 노출  citeturn6view0
	3.	MCP Catalog에 등록해 카탈로그 기반 검색·헬스체크·버전 관리 흐름에 통합

3. 배경
	•	사내 여러 AI Agent가 비트코인 온체인·메인풀 실시간 데이터를 필요로 함.
	•	기존 mempool WebSocket 연동은 각 팀이 개별로 구현 → 중복·비표준·운영 부담.
	•	MCP 서버로 표준화하면 카탈로그 기반 Discovery, 자동 헬스체크, 재사용, 보안 경로 통제가 가능.

4. 범위(Scope)

포함

항목	설명
FastMCP Python 서버	FastMCP 2.0 기반 Stand‑alone Python 서버
Tool 정의	실시간 스트림 구독·해제·1회성 pull 지원
MCP Catalog 통합	등록/헬스체크/메타데이터 스키마 작성
GitHub CI 워크플로	린트, 테스트, 컨테이너 빌드, GHCR push
Helm 차트	기본 K8s 배포 템플릿

제외 (MVP 단계)
	•	TLS 종단 간 암호화(Cluster 내부 mTLS 구성은 추후)
	•	인증·인가(OAuth / API Key 등)
	•	멀티 체인(Ethereum mempool 등) 지원

5. 사용자 시나리오 & 태스크 플로우
	1.	LLM Agent가 “BTC mempool 용량이 300 MB 이상일 때 알림” 로직 작성.
	2.	Agent는 MCP Catalog에서 mempool-ws 서버의 stream_stats 도구를 선택해 subscribe(call‑backs 옵션).
	3.	FastMCP 서버는 mempool WebSocket에서 stats 채널을 구독해 이벤트를 받은 뒤 MCP 스트림으로 재전달.
	4.	Agent는 수신된 JSON payload를 해석해 조건 충족 시 알림 발송.

6. 기능 요구사항

6.1 Tool 명세

| Tool ID | 입력 파라미터 | 출력 | 설명 |
| —|—|—|—|
| stream_blocks | want: bool=True | 실시간 블록 헤더 JSON 객체 | 새 블록이 생성될 때마다 이벤트 push |
| stream_mempool_blocks | want: bool=True | 예상 차기 블록 template 목록 | mempool‑blocks 채널 래핑 |
| stream_stats | want: bool=True | mempoolInfo JSON | 네트워크 통계 |
| stream_live2h | want: bool=True | fee histogram 배열 | 2시간 라이브 차트 데이터 |
| track_address | address: str | Tx 배열 | 지정 주소와 관련된 mempool·confirmed Tx 스트림 |
| health | – | {status: "ok"} | 외부 ping (Catalog 헬스체크용) |

참고: 모든 스트림 도구는 Async Generator 형태로 구현하며, 호출자가 for event in tool(): … 패턴으로 소비.

6.2 연결 관리
	•	단일 WebSocket 커넥션 풀을 유지하여 채널별 multiplexing.
	•	MCP client disconnect 시 자동 un‑subscribe 및 자원 정리.

6.3 오류 처리
	•	Upstream 연결 실패 → MCP MCPUpstreamError raise (retry back‑off 내장).
	•	mempool 메시지 파싱 오류 → discard & warn log.

7. 외부 API 연동 상세

sequenceDiagram
    participant MCP_Server
    participant Mempool_WS
    MCP_Server->>Mempool_WS: OPEN ws://…/api/v1/ws
    Note left of MCP_Server: action:"want", data:[…]
    Mempool_WS-->>MCP_Server: JSON events
    MCP_Server-->>>MCP_Client: yield event

	•	Endpoint: wss://mempool.space/api/v1/ws citeturn6view0
	•	기본 subscribe 메시지: {"action":"want","data":["blocks",…]}
	•	주소 추적: {"track-address":"<bech32|base58 주소>"} citeturn6view0

8. 시스템 아키텍처

flowchart LR
    subgraph Runtime
        direction TB
        A[MCP Client<br/>Agent App]
        B[FastMCP Server<br/>mempool-ws]
        C[Mempool.space WS]
        A --MCP Tools--> B
        B --WS--> C
    end
    subgraph Infra
        B -.Deployed via Helm-> K8s[(k8s cluster)]
        B --Prometheus exporter--> Mon[(Prom/Grafana)]
    end

	•	FastMCP 서버는 ASGI (Uvicorn) + FastAPI로 구동.
	•	aiohttp or websockets 라이브러리로 upstream WS 관리.

9. 비기능 요구사항 (NFR)

카테고리	목표
Latency	95‑percentile < 1 sec (Agent 수신 기준)
Availability	99.5 % / 월
Observability	request/stream/failure 메트릭 → Prometheus export
Resource	Pod CPU 0.1 core avg, RAM < 256 MiB

10. 개발 환경 & 스택
	•	Python 3.11, FastMCP 2.0 (official SDK 포함)  citeturn7view0
	•	Poetry or uv for dependency.
	•	Lint: ruff, mypy.
	•	Test: pytest‑asyncio, httpx.
	•	Container: distroless python:3.11‑slim.

11. 구현 단계 (Step‑by‑Step)

단계	설명	산출물
0	PoC: 단일 stream_blocks tool 구현 + 로컬 테스트	demo.py, README
1	커넥션 풀·채널 매핑 모듈 구현	ws_manager.py
2	모든 Tool 추가 + 에러 처리	tools.py
3	헬스체크 & 메트릭	health.py, metrics.py
4	GitHub CI / pytest green	.github/workflows
5	Dockerfile + Helm Chart	charts/mempool-ws
6	Catalog 등록 & User Doc	catalog.yaml

12. 테스트 전략
	•	Unit: 채널 파싱, back‑off 로직.
	•	Integration: Live mempool.ws 접속 → mock via websockets.serve.
	•	Load: Locust 10 rps virtual Agents.

13. CI/CD & 배포
	1.	Push → GitHub Actions: lint → test → docker build → GHCR push.
	2.	ArgoCD sync: Helm chart update → staging → prod.

14. 일정 (T‑0 기준 주 단위)
	•	W1: 요구사항 확정 & PoC 완료
	•	W2: 기능 완성 + 테스트 통과
	•	W3: Helm 배포, Catalog 등록
	•	W4: 관제 대시보드 + 가이드 문서

15. 리스크 & 대응

리스크	영향	대응
mempool.ws API 변경	데이터 포맷 불일치	버전 tag 및 fallback parser
WS 연결 불안정	스트림 단절	auto‑reconnect / exponential back‑off
Catalog 스펙 변경	등록 실패	FastMCP adapter 업데이트

16. 향후 확장 고려
	•	멀티‑체인(mempool Ethereum, BSV) 스트림 도구 추가.
	•	트리거 기반 푸시(예: 거래 수수료 > X sat/vB).
	•	User level API key 발행 및 mTLS 종단 암호화.
	•	Grafana JSON 패널 템플릿 제공.

17. 참고 자료
	•	mempool.space WebSocket API Q&A citeturn6view0
	•	FastMCP GitHub README citeturn7view0

⸻

End of Document
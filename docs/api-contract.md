# 조선소 운행 지원 공통 API·이벤트 계약

작성일: 2026-10-17 · 스키마 버전: 1 · 구현 전 계약 초안

프론트엔드와 백엔드가 공유하는 단일 기준이다. 아래 JSON은 형식 예시이며 측정 결과가 아니다. Pydantic 모델로 REST OpenAPI와 이벤트 JSON Schema를 생성하고, TypeScript 타입·수신 검증(Zod)은 이 Pydantic 산출물에서 생성하며 손으로 따로 정의하지 않는다. 공통 fixture는 저장소 루트 `fixtures/`에 두고 세 영역이 같은 파일로 계약 일치를 검사한다.

## 1. 공통 규칙

- 기본 경로: `/api/v1`.
- ID는 문자열, 거리 m, 속도 m/s, 기간 s, 로컬 좌표 m.
- 로컬 좌표는 x가 오른쪽, y가 위쪽이다. Canvas 화면 좌표의 y축 반전은 프론트에서만 수행한다. 간선 geometry는 시작 노드에서 종료 노드로 향하는 polyline 좌표 배열이며, 차량 보간에 사용한다.
- 네트워크 시각은 UTC ISO 8601, 시뮬레이션 시각은 `sim_time_s`.
- 목표 도착 시각은 `target_arrival_sim_s`, 남은 시간은 `arrival_in_s`로 구분.
- 알 수 없는 예측은 `null`이며 0으로 대체하지 않는다.
- 차량 상태에는 `run_id`, `map_version`, `agent_epoch`, `sample_seq`를 포함.
- 클라이언트 네트워크 TTL은 벽시계, 주행과 시간 예측은 시뮬레이션 시계 사용.
- 변경 명령은 `Idempotency-Key`와 필요한 `expected_version`을 사용.
- 동일 키·동일 본문은 기존 응답 반환, 동일 키·다른 본문은 409.
- 버전 충돌은 409, 입력 검증 실패는 422, 인증 실패 401, 권한 없음 403.
- 오류 형식: `{"error":{"code":"VERSION_CONFLICT","message":"상태가 변경되었습니다.","request_id":"req-1"}}`.

## 2. REST API

| Method | 경로 | 권한 | 입력·출력 |
|---|---|---|---|
| GET | `/health` | 로컬 상태 확인 | 서비스 생존 상태 |
| POST | `/sessions` | 없음(설치 기기) | 본문 없음 → 서버가 배정한 차량 범위 세션 쿠키, 배정 불가 409 |
| DELETE | `/sessions/current` | 세션 | 세션 종료 |
| GET | `/me` | 세션 | 역할, 허용 차량 ID |
| GET | `/maps/current` | 세션 | 지도·노드·간선·map_version |
| GET | `/vehicles` | 관리자/자기 차량 | 허용 범위 차량 목록 |
| GET | `/state` | 세션 | 해당 역할의 전체 스냅샷 |
| PUT | `/vehicles/{id}/destination` | 해당 운전자/관리자 | destination_node_id 또는 null, expected_version → 경로/버전 |
| POST | `/guidance/{id}/ack` | 해당 운전자 | guidance_version → 수신 확인 결과 |
| PUT | `/edges/{id}/closure` | 관리자 | closed, expected_version → map_version |
| PUT | `/vehicles/{id}/priority` | 관리자 | priority, expected_version → vehicle_version |
| POST | `/telemetry/batches` | 차량 에이전트 | 아래 배치 구조 → 수락·중복·거부 내역 |
| POST | `/runs` | 관리자 | scenario_id, seed, prediction_mode, coordination_enabled → run_id |
| POST | `/runs/{id}/commands` | 관리자 | action: start/pause/resume/stop → run 상태 |
| GET | `/runs/{id}/metrics` | 관리자 | 예측·통행 지표, 정의·단위·완료 여부 |

세션은 로그인 없이 발급한다. 운전자 세션의 차량은 서버가 시나리오 순서로 배정하고, 관리자 세션은 서버 호스트(loopback) 접속에만 발급한다. 상세는 [백엔드 기획서 9장](../backend/docs/proposal.md)을 따른다.

목적지 변경 응답: `route_version`, `map_version`, `edge_ids`, `estimated_total_s`, `route_status`.
`route_status`는 FOUND / NO_PATH / UNAVAILABLE. 경로 없음은 정상 도메인 결과이며 빈 경로를 통과 가능 경로로 취급하지 않는다.

실행 모드 `prediction_mode`: BASELINE / BASE_MODEL / ADAPTIVE. `coordination_enabled`는 별도 boolean. 실행 중 변경하지 않는다. 동시에 활성 실행은 한 개, 추가 생성은 409. 비교하려면 기존 실행을 종료하고 같은 시드의 새 실행을 만든다.

## 3. 차량 입력 예시

```json
{
  "run_id": "run-001",
  "vehicle_id": "truck-A",
  "agent_epoch": "agent-boot-001",
  "samples": [
    {
      "sample_seq": 101,
      "map_version": 3,
      "sim_time_s": 20.0,
      "observed_at": "2026-10-17T03:00:00Z",
      "edge_id": "edge-01",
      "x_m": 120.0,
      "y_m": 35.0,
      "speed_mps": 2.5,
      "direction": "FORWARD"
    }
  ],
  "events": [],
  "predictions": []
}
```

이벤트 필수 필드: `event_id`, `kind`(APPROACH/ENTER/EXIT/WAITING), `zone_id`, `sim_time_s`, `sample_seq`. 수신 시각은 서버가 부여한다. 임의 EXIT로 점유를 해제하지 않도록 실행·차량·구간·활성 점유 토큰과 일치하는지 검증한다. 정상 예약 없는 진입도 감지하면 UNKNOWN으로 전환해 상대편 예약을 차단한다.

예측 필드: `prediction_id`, `prediction_kind`(APPROACH/TRAVERSE), `target_id`, `made_at_sim_s`, `base_s`, `correction_s`, `predicted_s`, `margin_s`, `quality`(VALID/INSUFFICIENT/STALE), `model_version`, `feature_schema_version`, `source_sample_seq`. 수치는 유한·비음수(보정값 제외), 만료·다른 지도·알 수 없는 모델 버전이면 사용하지 않는다.

## 4. WebSocket

엔드포인트: `/api/v1/ws`. 인증된 역할의 채널만 서버가 선택해 전달한다. 운전자는 자기 안내와 접근 관련 최소 정보만 받는다.

```json
{
  "schema_version": 1,
  "connection_id": "conn-01",
  "run_id": "run-001",
  "seq": 42,
  "type": "guidance.changed",
  "server_time": "2026-10-17T03:00:00Z",
  "sim_time_s": 20.0,
  "payload": {
    "guidance_id": "g-01",
    "guidance_version": 2,
    "vehicle_id": "truck-A",
    "state": "WAIT",
    "zone_id": "zone-01",
    "waiting_node_id": "wait-east",
    "reason_code": "OPPOSING_PRIORITY",
    "arrival_in_s": 35.0,
    "valid_until_sim_s": 25.0
  }
}
```

| 이벤트 | payload |
|---|---|
| `state.snapshot` | map_version, run 상태, vehicles, routes, guidance, reservations |
| `vehicles.updated` | 변경된 차량의 전체 항목 배열; vehicle_version으로 비교 |
| `route.changed` | 차량 ID, route_version, 경로 상태·간선 목록 |
| `guidance.changed` | 위 예시 구조 |
| `reservation.changed` | zone_id, reservation_version, state, owner_vehicle_id |
| `map.changed` | map_version, 변경 간선 |
| `run.changed` | 실행 상태, seed, 모드, sim_time_s |
| `metrics.updated` | 누적 지표·표본 수 |
| `heartbeat` | 서비스 상태, run 상태 |

`seq`는 필터링 후 각 연결에 전달하는 메시지 순서로 증가한다. 연결 최초와 재동기화 시 스냅샷의 상태·seq를 원자적으로 확보한 뒤 이후 변경을 전달한다. 새 연결은 새 connection_id와 seq를 사용한다. 누락 발견 시 클라이언트는 `{"type":"resync.request"}`를 보내고 새 스냅샷을 기다린다. 이 메시지에는 추가 필드가 필요 없다.

느린 클라이언트는 무제한 이벤트를 쌓지 않고 연결 종료 후 스냅샷으로 복구한다. 통행 안내는 실시간 이벤트 로그만 믿지 않고 재접속 스냅샷에도 포함한다.

## 5. 상태 정의

- 안내: IDLE / ROUTE / APPROACH / WAIT / RESERVED / UNKNOWN.
- 구간: FREE / RESERVED / OCCUPIED / UNKNOWN.
- 실행: CREATED / RUNNING / PAUSED / STOPPED / COMPLETED / FAILED.
- 연결: CONNECTING / SYNCING / LIVE / STALE / DISCONNECTED.

안내 TTL 만료나 통신 끊김은 UNKNOWN을 의미한다. 구간 해제나 통과 허용을 의미하지 않는다. 예약 차량이 진입 전 이탈한 것이 확인되면 예약 취소 가능. 확인할 수 없으면 UNKNOWN. OCCUPIED는 검증된 실제 이탈로만 해제한다.

## 6. 데모 기본 주기

- 시뮬레이터 tick: 100ms(10Hz).
- 차량 상태 전송: 200ms(5Hz).
- 예측 갱신: 1초 또는 중요 상태 변화.
- heartbeat: 1초.
- 네트워크 갱신이 3초 이상 없으면 STALE 표시.

이는 데모 초기 설정이며 현장 안전 임계값이 아니다. 재생 속도를 변경하면 시뮬레이션 시간만 배속하고 heartbeat 시간은 변경하지 않는다.

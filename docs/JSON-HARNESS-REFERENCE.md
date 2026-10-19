# 기존 JSON 하네스 전환 안내

JSON 기반 작업 관리 CLI는 Markdown 기반 읽기 전용 검사 도구로 교체했다.

- `backlog/*.json`은 기획 참고 초안으로 보존하며 검사·상태 관리에 사용하지 않는다.
- `check`는 phase Markdown의 구조와 의존성을 검사한다.
- `board`는 Markdown 체크리스트 현황을 표시한다.
- `start`, `block`, `resume`, `run`, `done`, `next`는 지원하지 않는다.
- 구현 착수 승인은 `scripts/git_flow.py start`가 검사한다.
- 실제 검증 명령을 실행하고 결과·증빙·제약은 해당 phase Markdown에 기록한다. JSON 증빙 파일은 요구하지 않는다.

문서 형식과 사용법은 [현재 하네스 안내](HARNESS.md)를 따른다. 문서 구조 검사 통과는 제품 테스트 통과나 구현 승인을 의미하지 않는다.

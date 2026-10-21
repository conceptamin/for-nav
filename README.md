# for-nav

울산 외국인 근로자 산업보건 내비게이터(가칭). 울산 일터에서 다친 외국인 근로자가 모국어로 말하면 응급 여부, 먼저 상담할 비용 경로, 지금 열린 의원·약국을 안내하고 의사에게 보여 줄 한국어 요약 카드를 만든다. 진단하지 않는 소통 보조 서비스다.

팀 콘셉타민 · 울산 청년 AX 리더십 헬스케어·서비스 AI 트랙 · 해커톤 2026-10-30~31 · 본선 2026-11-06

## 폴더

```text
docs/api-contract.md   공통 API 계약 (세 영역 공유)
fixtures/              공통 테스트 데이터 (계약 예시, 비용 경로 정답 사례)
frontend/              모바일 웹 (React·Vite)          문서: frontend/docs/
backend/               API·규칙 엔진·LLM 호출 (FastAPI)  문서: backend/docs/
modeling/              응급 감지 모델·테스트셋·평가       문서: modeling/docs/
```

- 기획서: [프론트](frontend/docs/proposal.md) · [백엔드](backend/docs/proposal.md) · [모델링](modeling/docs/proposal.md)
- 영역별 규칙·실행 명령: [프론트](frontend/AGENTS.md) · [백엔드](backend/AGENTS.md) · [모델링](modeling/AGENTS.md)

## 일정

| 날짜 | 목표 |
|---|---|
| 10-21 | 개발 환경 세팅 완료 · 개발 착수 |
| 10-22 | API 계약·테스트셋 고정 |
| 10-23 | 첫 흐름 연결: 텍스트 입력 → 응급 확인 → 비용 경로 → 요약 카드 |
| 10-30~31 | 해커톤: 음성 입력, 지금 갈 수 있는 곳 |
| 11-03 | 기능 동결 |
| 11-06 | 본선 발표 |

## 작업 방식

[작업 약속](CONTRIBUTING.md)을 따른다. 요약: main은 PR로만 바꾸고, 리뷰를 받은 뒤 CI가 통과하면 병합한다.

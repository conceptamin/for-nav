# YardPilot

가상 조선소 차량 운행 지원 MVP.

## 폴더

```text
docs/api-contract.md   공통 API·이벤트 계약 (세 영역 공유)
fixtures/              공통 테스트 데이터
frontend/              프론트 (React·Vite)       문서: frontend/docs/
backend/               백엔드·시뮬레이터 (FastAPI) 문서: backend/docs/
modeling/              차량 예측·학습             문서: modeling/docs/
```

- 기획서: [프론트](frontend/docs/proposal.md) · [백엔드](backend/docs/proposal.md) · [기술·모델](modeling/docs/proposal.md)
- 영역별 규칙·실행 명령: [프론트](frontend/AGENTS.md) · [백엔드](backend/AGENTS.md) · [모델링](modeling/AGENTS.md)

## 작업 방식

[작업 약속](CONTRIBUTING.md)을 따른다. 요약: main은 PR로만 바꾸고, 1명 승인과 CI 통과 후 병합한다.

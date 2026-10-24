# for-nav

콘셉타민: 외국인 주민이 모국어 텍스트 채팅으로 의료이용의 어려움을 설명하고, AI가 정리한 내용을 센터 상담사가 이어받아 실제 지원으로 연결하는 상담 서비스.

부상자에 한정하지 않고 병원 이용·예약·서류·통역·보험·의료비 상담을 다룬다. 보험은 상담에 필요한 가입·자격 확인 상태를 정리하며, 특정 치료의 보험 적용 여부를 판단하지 않는다.

팀 콘셉타민 · 울산 청년 AX 리더십 헬스케어·서비스 AI 트랙 · 해커톤 2026-10-30~31 · 본선 2026-11-06

## 기획과 구현 상태

- **현재 기획 기준:** [콘셉타민 서비스 기획안](docs/proposal.md) (2026-10-24).
- 흐름: 언어 선택 → 채팅 → 필요한 정보 확인 → 요약 검토·동의 → 센터 접수 → 상담·연계 → 결과 기록.
- 영역별 기획: [프론트](frontend/docs/proposal.md) · [백엔드](backend/docs/proposal.md) · [모델링·평가](modeling/docs/proposal.md).
- 보험 자동 조회는 이용 조건·외국인 인증·제공 항목 검증 전이며, 구현 완료 기능이 아니다.
- 기존 [API v1 초안](docs/api-contract.md)과 이전 phase 계획은 과거 기획의 참조다. 새 상담 저장·인증·인계 계약과 구현 phase는 별도 작성해야 한다.

## 폴더

```text
docs/proposal.md       공통 서비스 기획 기준
docs/git-convention.md 브랜치·커밋·PR 형식
docs/api-contract.md   이전 기획 API v1 초안 (전환 예정)
fixtures/              기존 계약 예시·비용 경로 정답 사례
frontend/              사용자 모바일 웹·상담사 화면 (React·Vite)
backend/               상담 API·AI 호출·저장·연동 설계 (FastAPI)
modeling/              대화·요약·번역 품질 평가, 기존 모델 연구 자료
```

폴더 설명은 목표 책임이며 구현 완료를 뜻하지 않는다. 실행·검증 명령은 [프론트](frontend/AGENTS.md) · [백엔드](backend/AGENTS.md) · [모델링](modeling/AGENTS.md)을 참고한다.

## 다음 단계

센터 업무·지원 언어 확인 → 보험 연동 가능성 검증 및 인증·저장 정책 설계 → 새 API 계약·phase 작성 → 상담 접수부터 결과 기록까지 구현·검증. 세부 개발 일정은 새 범위에 맞춰 재산정한다.

## 작업 방식

[작업 약속](CONTRIBUTING.md)과 [Git 컨벤션](docs/git-convention.md)을 따른다. main은 PR로만 바꾸고, 리뷰를 받은 뒤 CI가 통과하면 병합한다.

## 백로그 승인 요청

- 문서: backlog/<영역>/phase-XX.md
- 목표 및 범위:
- 제외 범위:
- 선행 작업 및 완료 증거:
- 수용 기준:
- 검증 방법:

phase 문서만 변경하고 develop을 대상으로 제출합니다.
지정 승인자가 최신 커밋을 승인하고 Squash and merge로 병합한 뒤에만 구현 요청이 가능합니다.
병합 후 사람이 `python3 scripts/request_impl.py backlog/<영역>/phase-XX.md`로 이 PR에
`implement <문서> <병합 SHA>` 댓글을 남기고 AI에게 작업을 요청합니다.

# fixtures

세 영역이 같이 쓰는 테스트 데이터.

```text
fixtures/contract/      계약 예시 요청·응답 JSON (백엔드가 만들고 프론트·백엔드 테스트가 읽음)
fixtures/route-cases/   비용 경로 가상 사례와 정답 (콘텐츠 담당 작성)
```

## route-cases

목표 30개. 정답은 규칙을 만들지 않은 사람(콘텐츠·발표 담당)이 [계약 4장](../docs/api-contract.md)의 질문과 기획안 5장 근거 자료만 보고 쓴다. 가능하면 지원센터·노무 지식이 있는 사람이 일부를 검토한다. 규칙 담당과 AI는 정답을 고치지 않는다. 정답이 틀렸다고 보이면 PR에 근거를 적어 담당자에게 묻는다.

한 사례당 JSON 파일 하나(`case-01.json` …):

```json
{
  "id": "case-01",
  "story": "동구 조선소 용접공. 작업 후 눈 통증. 건강보험증 있음.",
  "answers": { "q1": "yes", "q2": "yes", "q3": null },
  "expected_route": "WORK_INJURY",
  "written_by": "콘텐츠 담당 이니셜",
  "reviewed_by": null
}
```

`expected_route`는 `WORK_INJURY` / `HEALTH_INSURANCE` / `ULSAN_MEDICAL_AID` / `SUPPORT_CENTER` 중 하나다.

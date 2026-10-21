# for-nav 공통 API 계약

작성일: 2026-10-21 · 스키마 버전: 1 · 초안 (2026-10-22 고정 목표)

프론트엔드·백엔드·모델링이 공유하는 단일 기준이다. 아래 JSON은 형식 예시이며 측정 결과가 아니다. 백엔드 Pydantic 모델이 OpenAPI의 원본이고, 프론트 타입과 수신 검증은 이 산출물에서 만든다. 손으로 따로 정의하지 않는다. 예시 요청·응답은 루트 `fixtures/contract/`에 두고 프론트·백엔드 테스트가 같은 파일을 읽는다.

## 1. 공통 규칙

- 기본 경로: `/api/v1`. 인증 없음(데모). 서버는 요청·응답을 저장하지 않고 요청 본문을 로그에 남기지 않는다.
- 언어 코드: `en`, `vi`. 근로자에게 보이는 문구는 요청의 `lang`으로, 의사용 요약은 항상 한국어(`ko`)로 낸다. 세 번째 언어는 원어민 검수자가 확보될 때만 추가한다.
- 알 수 없는 값은 `null`이다. 빈 문자열·0·추측값으로 채우지 않는다.
- 시각: 진료 시간 조회의 `at`은 울산 현지 시각 `HH:MM`(24시간), 요일은 `mon`~`sun`. 응답의 생성 시각은 UTC ISO 8601.
- 정보 기준일 `info_as_of`(YYYY-MM-DD)와 안내 문구 `disclaimer`는 제도·기관 정보를 담은 모든 응답(`/route`, `/guide`, `/hospitals`)에 포함한다. `/triage`·`/summary`는 제도·기관 정보를 담지 않으므로 `info_as_of`가 없다.
- 오류 형식: `{"error":{"code":"CONSENT_REQUIRED","message":"요약 카드를 만들려면 동의가 필요합니다.","request_id":"req-1"}}`.
- 입력 검증 실패 422, 없는 경로 404, LLM 호출 실패 503(`LLM_UNAVAILABLE`). 503이어도 응급 판단은 내려야 하므로 `/triage`는 LLM 실패 시에도 200으로 응급 결과를 돌려준다(3장).

## 2. 엔드포인트

| Method | 경로 | 방식 | 입력 → 출력 |
|---|---|---|---|
| GET | `/health` | 정적 | 생존 상태 (구현됨) |
| POST | `/triage` | 규칙 + 응급 감지 모델 + LLM 추출 | 모국어 텍스트 → 응급 여부, 작업 맥락, 되물을 항목, 진료과 |
| POST | `/route` | 규칙 | Q1~Q3 답 → 먼저 상담할 경로, 안내 문구, 연결 기관 |
| POST | `/summary` | LLM | 근로자가 고른 항목 + 동의 → 의사용 한국어 요약 |
| GET | `/guide` | 정적 콘텐츠 | `lang` → 산재 상담 절차, 연락처 |
| GET | `/hospitals` | 공공 데이터 또는 mock | `at`, `day`, `district`, `department` → 열린 의원·약국·응급실 |

음성 입력은 해커톤 단계에서 붙인다. 엔드포인트(`POST /transcribe` 예정)는 그때 이 문서에 추가한다.

## 3. POST /triage

요청:

```json
{
  "lang": "vi",
  "text": "Chiều nay sau khi hàn, mắt tôi rất đau. Tôi đã tháo kính bảo hộ một lúc.",
  "answers": {}
}
```

`answers`는 되묻기 버튼으로 받은 값이다. 키는 아래 `context` 필드 이름과 같다.

응답:

```json
{
  "emergency": {
    "is_emergency": false,
    "by_rule": false,
    "by_model": false,
    "matched_rules": [],
    "model_score": 0.07,
    "model_version": "emergency-tfidf-lr-0.1.0"
  },
  "context": {
    "symptom": "눈 통증",
    "body_part": "눈",
    "onset": "오늘 오후",
    "task_type": "용접",
    "ppe_worn": "partial",
    "incident": "보안경을 잠깐 벗음",
    "work_related": null
  },
  "missing_fields": ["work_related"],
  "department": { "code": "ophthalmology", "label_ko": "안과" },
  "notice": "증상이 심해지면 119에 전화하세요.",
  "context_status": "OK"
}
```

- 응급 판단은 `by_rule OR by_model`이다. LLM 결과를 쓰지 않는다. 모델을 쓸 수 없으면 `by_model`·`model_score`·`model_version`이 `null`이고 규칙만으로 판단한다.
- `is_emergency`가 `true`면 프론트는 다른 화면보다 119 화면을 먼저 띄운다. 이때 `context`는 채워질 수도, `null`일 수도 있다.
- `notice`는 응급 여부와 상관없이 항상 있다.
- `ppe_worn`: `yes` / `no` / `partial` / `null`. `work_related`: `yes` / `no` / `unsure` / `null`. 이 값은 근로자 응답의 기록이며 산재 판정이 아니다.
- `context_status`: `OK` / `LLM_UNAVAILABLE`. LLM이 실패하면 `context`는 `null`, `missing_fields`는 전체 항목, 응급 결과는 그대로 낸다.
- 진료과 코드: `emergency`, `ophthalmology`(안과), `orthopedics`(정형외과), `dermatology`(피부과), `internal_medicine`(내과), `family_medicine`(가정의학과, 대응 표에 없을 때). 증상·부위에서 진료과로 가는 대응 표는 백엔드 규칙이다.
- `department`: `is_emergency`가 `true`면 `{ "code": "emergency", "label_ko": "응급실" }`이다. 응급이 아니고 `context`가 `null`이면(LLM 실패) `department`도 `null`이다. 추측해서 `family_medicine`으로 채우지 않는다.

## 4. POST /route

질문(근로자 언어로 번역해 표시):

| 질문 | 답 |
|---|---|
| `q1` 일하는 중에 다쳤거나, 일 때문에 생긴 증상인가요? | `yes` / `no` / `unsure` |
| `q2` 건강보험증이 있나요? | `yes` / `no` / `unsure` |
| `q3` 울산에서 90일 이상 살거나 일했나요? | `yes` / `no` |

결정 규칙(위에서 처음 맞는 줄):

| 조건 | `route` |
|---|---|
| `q1` = `yes` 또는 `unsure` | `WORK_INJURY` (산재 상담) |
| `q1` = `no`, `q2` = `yes` | `HEALTH_INSURANCE` (건강보험 일반 진료) |
| `q1` = `no`, `q2` = `unsure` | `SUPPORT_CENTER` (지원센터 상담, 건강보험 가입 확인 방법 함께) |
| `q1` = `no`, `q2` = `no`, `q3` = `yes` | `ULSAN_MEDICAL_AID` (울산 의료비 지원, 입원·수술 시) |
| `q1` = `no`, `q2` = `no`, `q3` = `no` | `SUPPORT_CENTER` |

- 경로에 필요 없는 질문의 답은 `null`로 보낸다. 필요한 답이 빠지면 422 `MISSING_ANSWER`. 필요 없는 답이 `null`이 아니어도 422로 막지 않고 경로 결정에 쓰지 않는다.
- 질문 순서: 화면은 Q1을 먼저 묻는다. `/triage`의 `context.work_related`가 `null`이 아니면 그 값을 Q1의 기본 선택으로 채우고 근로자가 확인하거나 바꾼다. `q1`이 `yes`·`unsure`면 Q2까지 묻고(아래 `insurance_note`용) Q3는 건너뛴다. `q1`이 `no`면 위 표에서 필요한 질문만 묻는다.
- 예외: `q1`이 `yes`·`unsure`여도 `q2`를 보낼 수 있다. 이때 결과는 `WORK_INJURY` 그대로이고 `insurance_note`에 건강보험 여부를 적는다. 산재 승인 전 진료비 납부 방식이 확인되기 전까지 문구는 "상담으로 확인하세요"다.

요청·응답:

```json
{ "lang": "vi", "q1": "no", "q2": "no", "q3": "yes" }
```

```json
{
  "route": "ULSAN_MEDICAL_AID",
  "message": "Nếu bác sĩ nói cần nhập viện hoặc phẫu thuật, hãy hỏi về hỗ trợ chi phí y tế của Ulsan.",
  "conditions": ["입원·수술이 필요할 때 지원", "본인 부담 약 10%", "외래 진료는 지원되지 않을 수 있음"],
  "insurance_note": null,
  "contacts": [
    { "name_ko": "대한적십자사 울산지사", "phone": null, "verified": false }
  ],
  "disclaimer": "지원 여부는 각 기관이 최종 결정합니다.",
  "info_as_of": "2026-10-21"
}
```

- `verified: false`인 연락처는 화면에 "상담으로 확인하세요"로 표시하고 번호를 지어내지 않는다.
- 참여 병원을 표기할 때 민간 "울산병원"과 "근로복지공단 울산병원"을 반드시 구분한다.
- 정답 사례는 `fixtures/route-cases/`에 있다(콘텐츠 담당 작성).

## 5. POST /summary

요청:

```json
{
  "lang": "vi",
  "consent": true,
  "include": ["symptom", "onset", "task_type", "incident"],
  "context": {
    "symptom": "눈 통증",
    "body_part": "눈",
    "onset": "오늘 오후",
    "task_type": "용접",
    "ppe_worn": "partial",
    "incident": "보안경을 잠깐 벗음",
    "work_related": null
  }
}
```

응답:

```json
{
  "summary_ko": "오늘 오후 용접 작업 후 눈 통증이 시작되었습니다.",
  "items": [
    { "field": "symptom", "label_ko": "증상", "value_ko": "눈 통증" },
    { "field": "onset", "label_ko": "시작 시점", "value_ko": "오늘 오후" },
    { "field": "task_type", "label_ko": "작업 유형", "value_ko": "용접" },
    { "field": "incident", "label_ko": "사고 상황", "value_ko": "보안경을 잠깐 벗음" }
  ],
  "generated_at": "2026-10-21T10:00:00Z",
  "disclaimer": "이 카드는 근로자의 진술을 정리한 것이며 진단이 아닙니다."
}
```

- `consent`가 `true`가 아니면 422 `CONSENT_REQUIRED`이고 LLM을 호출하지 않는다.
- `include`에 없는 필드는 LLM 입력에서 빼고 응답 어디에도 나오지 않는다. 기본값은 프론트에서 "모두 포함"으로 보여 주고 근로자가 뺀다.
- `context`의 `null` 항목은 카드에 넣지 않는다.

## 6. GET /guide

`GET /api/v1/guide?lang=vi` → 산재 상담 절차(단계 배열), 보관할 것(진료 기록·영수증·근무 기록), 연락처(`verified` 포함), `disclaimer`, `info_as_of`. 사업주가 돕지 않아도 근로자가 직접 신청할 수 있다는 안내를 포함한다. 체류 자격은 언급하지 않는다.

## 7. GET /hospitals

`GET /api/v1/hospitals?at=19:00&day=mon&district=dong-gu&department=ophthalmology`

- `district`: `jung-gu`, `nam-gu`, `dong-gu`, `buk-gu`, `ulju-gun`. 구·군보다 자세한 위치는 받지 않는다.
- 응답 항목: `name_ko`, `kind`(`clinic` / `pharmacy` / `er`), `department`, `open_until`(`HH:MM` 또는 `null`), `address_ko`, `phone`, `source`(`mock` / `public_api`), `info_as_of`.
- 공공 API 확인 전까지는 동구·북구 기관 10~20곳의 mock 데이터를 쓴다. mock 항목은 `source: "mock"`으로 표시하고 화면에도 예시 데이터임을 밝힌다.

## 8. 미결 사항

| 항목 | 확인처 | 영향 |
|---|---|---|
| 울산 의료비 지원 2026년 운영 여부, 산재 해당자 제외, 외래 지원, 신청 창구 | 울산시 | `/route` `ULSAN_MEDICAL_AID` 조건 문구 |
| 울산외국인근로자지원센터 연락처·방문 시간 | 지원센터 | `contacts` |
| 근로복지공단 고객센터·다국어 상담 번호 (1350은 고용노동부) | 근로복지공단 | `contacts`, `/guide` |
| 산재 승인 전 진료비 납부 방식과 환급 절차 | 근로복지공단 | `insurance_note` |
| 요일별 진료 시간 공공 API | 공공데이터포털 | `/hospitals` `source` |

확인되면 이 표에서 지우고 해당 장의 문구와 `info_as_of`를 갱신한다.

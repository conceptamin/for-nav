# Modeling Phase 01 — 환경, 테스트셋 고정, 기본 모델

목표일: 테스트셋 고정 2026-10-22, 기본 모델 2026-10-24

## 목표

`modeling/`에 uv 프로젝트를 만들고, 데이터 폴더와 분할 규칙을 정한 뒤 최종 테스트셋을 10-22에 고정한다. TF-IDF + 로지스틱 회귀 기본 모델(v0)을 학습·평가하고 백엔드가 읽을 JSON으로 내보낸다.

## 범위

포함:

- `modeling/`에 uv 프로젝트(`pyproject.toml`, `uv.lock`, `.python-version` 3.11). 직접 의존성(scikit-learn, pandas, pytest, Ruff, mypy)을 PyPI·공식 문서로 확인해 정확한 버전으로 고정하고 출처와 날짜를 기록한다. 백엔드와 같은 `exclude-newer` 기준을 쓴다.
- 데이터 형식: 한 줄에 한 문장인 JSONL. 필드 `id`, `lang`, `text`, `label`(`emergency` / `non_emergency`), `source`(`synthetic` / `human` / `external:<이름>`), `scenario_id`.
- 분할 명령: 사람이 쓴 문장을 `scenario_id` 단위로 검증셋과 테스트셋으로 나눈다. 테스트셋 문장은 `data/human/`에서 빼서 `data/test/`로 옮기고, `data/human/`에는 검증셋만 남긴다. seed를 고정한다. 테스트셋 파일의 sha256을 이 문서에 기록한다.
- 학습 명령: `data/synthetic/`(과 쓰기로 정한 `data/external/`)으로 학습하고, 임계값은 `data/human/`(검증셋)에서 재현율 기준으로 정한다. 외부 데이터의 검증용 분할을 쓰면 수치를 출처별로 따로 출력한다.
- 평가 명령: `data/test/`만 읽어 재현율·정밀도·오탐률과 분자·분모, `lang`별 수치를 출력한다.
- 내보내기 명령: [기획서 5장](proposal.md)의 JSON과 기대 점수 예시 파일.
- 테스트: 학습 재현성(같은 seed → 같은 해시), 학습 명령의 `data/test/` 미열람, 평가 출력 형식.
- `.github/workflows/ci.yml`에 모델링 작업(ruff, mypy, pytest) 추가. main 룰셋의 필수 상태 검사에 `modeling`을 넣는 일은 저장소 소유자에게 요청한다.

제외:

- 비교 모델(다국어 임베딩, LLM 제로샷), 오분류 분석 라운드 (phase-02).
- 합성 문장 대량 생성 자동화. 이번 phase는 생성한 파일을 넣는 형식만 정한다.
- 백엔드에 모델 연결 (백엔드 phase-03).

## 작업 체크리스트

- [ ] 의존성 버전을 확인하고 uv 프로젝트를 만든다.
- [ ] 데이터 형식과 폴더를 만들고 `modeling/AGENTS.md`에 실행 명령을 등록한다.
- [ ] 콘텐츠 담당에게서 사람이 쓴 문장(80개 이상, 응급 30개 이상)을 받는다. 부족하면 개수와 함께 이 문서에 적는다.
- [ ] 분할 명령으로 테스트셋을 만들고 sha256과 응급·비응급 개수를 기록한다.
- [ ] 학습·평가·내보내기 명령과 테스트를 작성한다.
- [ ] v0 평가 결과를 분자·분모와 함께 기록한다.
- [ ] CI에 모델링 작업을 추가하고, 룰셋 필수 검사에 `modeling`이 들어갔는지 확인한다.

## 의존성

- 사람이 쓴 문장: 콘텐츠·발표 담당 산출물(테스트 문장 80개).
- [백엔드 phase-02](../../backend/docs/phase-02.md)의 응급 키워드 규칙: 모델 + 규칙 합산 평가는 phase-02에서 한다.

## 외부 데이터 확인 기록

확인일: 2026-10-21. 쓰기 전에 라이선스를 다시 확인하고 내려받은 파일의 sha256을 이 표에 더한다.

| 데이터 | 내용 | 라이선스 | 판단 |
|---|---|---|---|
| [PMR-Reddit-Train-Dev-Pool](https://huggingface.co/datasets/PortalPal-AI/PMR-Reddit-Train-Dev-Pool) | Reddit 의료 질문 글 859개(train 772, dev 87), 긴급도 `level` 1~6과 전문가 의견. 사람이 쓴 영어 글 | CC BY-NC 4.0 (Hugging Face 데이터 카드) | 사용 가능(비상업). 학습·검증 보강. 응급 라벨 변환 규칙(예: `level` 1 → `emergency`)은 논문의 등급 정의를 보고 정해 여기에 적는다 |
| [PMR-Reddit-Test-Pairs](https://huggingface.co/datasets/PortalPal-AI/PMR-Reddit-Test-Pairs) | 같은 출처의 긴급도 비교 쌍 1,502개 | CC BY-NC 4.0 | 쌍 비교 형식이라 이진 분류에는 직접 맞지 않음. Train-Dev-Pool과 글이 겹치는지 확인 전에는 쓰지 않음 |
| [PMR-Synth-Inboxes](https://huggingface.co/datasets/PortalPal-AI/PMR-Synth-Inboxes) | LLM이 만든 메시지 60개 | CC BY-NC 4.0 | 쓴다면 합성 문장으로 분류 |
| [ViMQ](https://github.com/tadeephuy/ViMQ) | 베트남 병원 온라인 상담 환자 질문 9,000개, 의도·개체명 라벨 | 저장소에 라이선스 표시 없음 | 사용 불가. 저작자에게 허락을 받으면 다시 검토 |
| [OSHA Severe Injury Reports](https://www.osha.gov/severe-injury-reports) | 미국 작업장 중상(절단·입원·실명) 신고 서술, 2015-01~2025-11 ZIP | 페이지에 명시 없음. 미국 연방정부 저작물(17 U.S.C. §105) | 사업주의 3인칭 보고서 문체라 근로자 문장으로 쓰지 않음. 시나리오 참고용. 사업장명·주소는 가져오지 않음 |

비상업 조건: 해커톤·본선 발표와 공공 시범 운영은 비상업 용도로 본다. 상업 서비스로 바뀌면 CC BY-NC 데이터로 학습한 모델을 다시 학습한다. Reddit 원문의 권리는 데이터셋 라이선스와 별개이므로 원문을 저장소에 다시 배포하지 않고, 내려받는 명령과 해시만 남긴다.

## 완료 조건

- [ ] `uv sync --locked`, Ruff, mypy strict, pytest가 통과하고 CI에서도 돈다.
- [ ] `data/test/`가 10-22 기준으로 고정돼 있고 sha256, 문장 수, 응급 문장 수(30개 이상)가 기록돼 있다.
- [ ] 학습 명령이 `data/test/`를 읽지 않음이 테스트로 확인된다.
- [ ] 같은 seed로 두 번 학습한 모델 JSON의 해시가 같다.
- [ ] v0 재현율·정밀도·오탐률이 분자·분모와 함께, 합성·사람 문장 기준으로 나뉘어 기록돼 있다.
- [ ] 내보낸 JSON이 pickle 없이 읽히고 `model_version`·데이터 해시·seed·임계값을 담는다.

## 검증 결과

아직 구현 전.

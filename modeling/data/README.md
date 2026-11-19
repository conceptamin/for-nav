# 데이터 출처

원본은 `data/raw/<출처>/`에 받은 바이트 그대로 둔다(git 제외). 내려받기와 검증:

```sh
uv run python scripts/download_data.py           # 없거나 해시가 다른 파일만 내려받은 뒤 검증
uv run python scripts/download_data.py --verify  # 내려받지 않고 해시만 검증
```

해시는 `src/fornav_modeling/data/download.py`에 고정돼 있고, 이 문서의 sha256과 같아야 한다(`tests/test_download.py`가 확인한다). 출처가 파일을 바꿔 검증이 실패하면 새 파일을 확인한 뒤 두 곳을 함께 고친다.

확인 날짜는 모두 **2026-10-27**이다. 응급도 모델용 PLOS ONE KTAS 데이터(`kaggle_triage/`)는 응급도 모델과 함께 지웠다(backlog 15, 기록은 git 이력).

## 요약

| 폴더 | 용도 | 출처 | 라이선스 | 학습·평가 사용 |
|---|---|---|---|---|
| `kaggle_symptom/` | 진료과 모델 A | Kaggle "Disease Symptom Prediction" | CC BY-SA 4.0 | 가능. 출처 표시 필요, 상업 이용 가능. 가공한 데이터를 배포하면 같은 라이선스(동일조건변경허락) |
| `hira/` | 질환 → 진료과 매핑, 모델 B 라벨 | 공공데이터포털, 건강보험심사평가원 | 공공누리 제1유형(출처표시) | 가능. 출처 표시 필요, 상업 이용·변경 가능 |
| `ddxplus/` | 진료과 모델 A 학습 데이터 확대(backlog 17) | figshare "DDXPlus Dataset (English)", Mila | CC BY 4.0 | 가능. 출처 표시 필요, 상업 이용·변경 가능. 동일조건 조건 없음 |

식별 정보(이름·연락처·기관명) 열은 두 출처 모두 **없음**. 가공 단계에서 지울 열도 없다. 아래 출처별 "식별 정보" 항목에 점검 내용을 적었다.

## kaggle_symptom — 진료과 모델 A

- 데이터: Kaggle "Disease Symptom Prediction", Pranay Patil·Pratik Rathod. https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset (버전 2, 2020-05-24)
- 내려받기: Kaggle API `GET https://www.kaggle.com/api/v1/datasets/download/itachi9604/disease-symptom-description-dataset?datasetVersionNumber=2` (zip). 토큰은 `KAGGLE_API_TOKEN` 환경변수나 `~/.kaggle/access_token`에서 읽는다. 토큰이 없으면 페이지에서 zip을 받아 `--kaggle-zip <경로>`로 넘긴다
- 라이선스: CC BY-SA 4.0 (Kaggle 메타데이터 `licenseName`). 설명에 "for reference and training purposes only, and actual data may vary"라고 적혀 있다 — 실제 환자 기록이 아니라 만든 사람이 구성한 표다
- 동일조건변경허락: 이 데이터를 가공한 표를 배포하면 CC BY-SA 4.0으로 내야 한다. 학습한 모델 가중치가 "가공물"인지는 정해진 해석이 없으므로, 모델 메타데이터에 출처와 라이선스를 적는다

| 파일 | sha256 | 행 | 열 |
|---|---|---|---|
| `dataset.csv` | `ebbd391c4ba4d64f57a00eb3d0a55f0ca9b920b0c5de6b9af4234e72519c9618` | 4,920 | 18: `Disease`, `Symptom_1`~`Symptom_17` |
| `Symptom-severity.csv` | `cb5a84b5ebde81bb18738b7e7733bcbc5abdc667b4376893fb1774d8c444bc8d` | 133 | 2: `Symptom`, `weight` |
| `symptom_Description.csv` | `e0581662e815509596707ebb5b31efb44539562b451ecef8c1246aa713b7d832` | 41 | 2: `Disease`, `Description` |
| `symptom_precaution.csv` | `49371294708232b928f68fc60e9837e5cab8b90d450b7bd90f7305795bb6d311` | 41 | 5: `Disease`, `Precaution_1`~`Precaution_4` |

- 형식: UTF-8 CSV, 머리글 1행. 질환 41종
- 식별 정보: 없음. 사람 단위 기록이 아니라 질환 → 증상 목록이다

## hira — 질환 → 진료과 통계

공공데이터포털 파일데이터 두 건. 형식과 집계 단위가 같아 05에서 같은 방식으로 읽는다.

- 형식: **CSV, cp949(EUC-KR) 인코딩**, 머리글 1행. 숫자 칸 뒤에 공백이 붙어 있다(예: `2 ,4 ,22`)
- 집계 단위: **진료년도 × 진료과목(또는 표시과목) × 주상병코드(KCD 3단 상병, 영문 1자 + 숫자 2자, 예 `A09`)**. 진료년도 2025(심사분 2026년 4월까지), 건강보험, 약국 제외, 양방
- 질병은 주상병 기준이라 최종 확정 진단과 다를 수 있다. 환자수는 범주 안에서만 중복 제거된 값이라 진료과끼리 단순 합산하면 중복이 생긴다
- 라이선스: 공공누리 제1유형(출처표시) — 상업 이용·변경 가능, 출처 "건강보험심사평가원" 표시
- 연간 갱신(차기 등록 예정 2027-08-14). 갱신되면 내려받기 URL(`atchFileId`)과 해시가 바뀐다

| 파일 | 원래 파일 이름 | sha256 | 행 |
|---|---|---|---|
| `hospital_department_disease_2025.csv` | 건강보험심사평가원_병원급이상 진료과목별 상병 통계_2025.csv | `cb3db8312d715a2af05fcef2fb184c4b15e76c02e07c4e3fca102044c06be00b` | 30,331 |
| `clinic_specialty_disease_2025.csv` | 건강보험심사평가원_의원급 표시과목별 상병 통계_2025.csv | `50ea3afc9ccb8eca4ce83bc684bb15ba319ac39bf959af4ed8a83a3ecefbba2c` | 22,598 |

- 병원급 이상: https://www.data.go.kr/data/15055567/fileData.do (수정일 2026-09-02)
  - URL: https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003676566&fileDetailSn=1&insertDataPrcus=N
  - 열(8): `진료년도`, `진료과목`, `주상병코드`, `환자수`, `명세서청구건수`, `입내원일수`, `보험자부담금(선별포함)`, `요양급여비용총액(선별포함)`
  - 진료과목 48종(치과·한방 진료과 포함), 주상병코드 1,663종
- 의원급: https://www.data.go.kr/data/15055564/fileData.do (수정일 2026-07-20)
  - URL: https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003678463&fileDetailSn=1&insertDataPrcus=N
  - 열(8): 위와 같고 `진료과목` 대신 `표시과목`
  - 표시과목 26종(`진단방사선과,영상의학과`처럼 쉼표가 든 값이 있어 따옴표로 감싸져 있다), 주상병코드 1,654종
- 식별 정보: 없음. 진료과목·상병 단위 집계이고 기관명·개인 열이 없다

## ddxplus — 진료과 모델 A 학습 데이터 확대(backlog 17)

확인 날짜 **2026-11-17**.

- 데이터: "DDXPlus Dataset (English)", Arsene Fansi Tchango 외(Mila). https://figshare.com/articles/dataset/DDXPlus_Dataset_English_/22687585 (버전 2, 게시 2026-03-09, DOI `10.6084/m9.figshare.22687585.v2`). 논문 https://arxiv.org/abs/2205.09148, 코드 https://github.com/mila-iqia/ddxplus
- 라이선스: **CC BY 4.0**(figshare API `GET https://api.figshare.com/v2/articles/22687585`의 `license`). 출처 표시가 필요하고 상업 이용·변경이 가능하다. 동일조건변경허락 조건은 없다. 그 밖의 이용 제한 문구는 README·figshare에 없다
- 생성 방식: 상용 의료 지식베이스와 규칙 기반 진단 시스템으로 만든 **합성 환자**다(GitHub README). 실제 환자 기록이 아니다. 급성기 진료를 전제로 만들어 호흡기·심장·감염 질환이 많다
- 내려받기: 로그인 없이 `https://ndownloader.figshare.com/files/<파일 id>`. 받은 md5가 figshare API의 `computed_md5`와 같은지 확인했다

| 파일 | 파일 id | 크기(바이트) | md5(figshare) | sha256 | 행 |
|---|---|---|---|---|---|
| `release_conditions.json` | 62561569 | 20,889 | `a992eadcff3099dd72e1820fbd2115aa` | `56edf4682d8e86a4209fc3a33932e50ce03d1cc1fecc326c26d5ef8fa5c24890` | 질환 49 |
| `release_evidences.json` | 40278013 | 120,263 | `0660962abe0bbf99e1fb77188c253597` | `281c78b044ae60514e28ecc9052d08a8225dd3e2db3f00f8788b99c47b05e0c0` | 근거 223 |
| `release_train_patients.zip` | 40278019 | 140,923,730 | `f75a78420ccb061951daa4db2d62139b` | `174ae1d56f36a15b7144838ecd214e1e1748a5369fc90c559529b6dc6ecfb218` | 1,025,602 |
| `release_validate_patients.zip` | 40278022 | 18,706,053 | `e4db88e9082f18410de6fd0cb7e74d18` | `625a96855becf0efe5da339fd3d440aa99597d48f784957a97dacc3fceaa7e40` | 132,448 |
| `release_test_patients.zip` | 40278016 | 18,986,243 | `6fd53d331cf19ed4439bf4f46b92ee94` | `ad3bb981f3453fd7abffb35cc595a1c02197e409c581bff97c1265c33eb00d23` | 134,529 |

- 형식: 환자 zip마다 확장자 없는 CSV 하나(`release_<part>_patients`), UTF-8, 머리글 1행. 열 6개: `AGE`, `DIFFERENTIAL_DIAGNOSIS`, `SEX`, `PATHOLOGY`, `EVIDENCES`, `INITIAL_EVIDENCE`. 환자 합계 **1,292,579**
- 근거: 223개 = 증상 110(이진 96, 범주 9, 다중 선택 5) + 병력 113. 근거 이름은 `E_<번호>`, 값은 `V_<번호>`이고 영어 문구는 `question_en`, `value_meaning[값].en`에 있다. 부위를 묻는 다중 선택 근거 넷(`E_55` 통증 부위, `E_57` 통증이 퍼지는 곳, `E_133` 발진 부위, `E_152` 부기 부위)은 같은 부위 값 165개(좌우 구분, "nowhere" 포함)를 쓴다
- 질환: 49종, 질환마다 `icd10-id`가 있다. KCD 3단으로 줄이면 질환별 코드 50개, 고유 48개다(폐렴 하나가 두 코드). 48개 모두 HIRA 2025 두 파일에 있다. Kaggle 질환과 같은 KCD 3단 코드를 쓰는 질환은 7개다
- 외상: 손상 코드(S·T)는 3개다. 자발성 늑골 골절(S22), 아나필락시스(T78), 스콤브로이드 식중독(T61)이고 열상·염좌·화상·외상성 골절은 없다
- 식별 정보: 없음. 합성 환자이고 열은 나이·성별·질환·근거뿐이다

## 안내 조합 표(`data/tables/department_guide*.csv`) — 진료과 정답

원본을 내려받지 않는다. 공개 안내 페이지에서 진료과 사실·URL·대조용 짧은 표기(페이지 제목 + 진료과 칸 값)만 표에 적었고 본문은 옮기지 않았다. 비영리 데모 검증용이다.

| 표 | 용도 | 출처 | 약관 확인 |
|---|---|---|---|
| `department_guide.csv`(29행) | 조정용(앙상블 가중치·폴백 기준값), backlog 05 | 서울대병원 N의학정보, 원주세브란스 직업환경의학과 소개 | 2026-10-28, backlog 05 `## 결과` |
| `department_guide_test.csv`(36행, 고정 31) | 최종 평가용, backlog 18. 고정 명령·평가 명령만 읽는다 | 세브란스병원 질환백과, 삼성서울병원 질환백과 | 2026-11-17, backlog 18 `## 결과` |
| `department_guide_train.csv`(446행) | 모델 B 학습용, backlog 19. 평가 조합과 같은 부위·증상 쌍이 있는 행과 평가 표에 쓴 페이지는 쓰지 않는다 | 서울대병원 N의학정보, 세브란스병원·삼성서울병원 질환백과 | 05·18과 같음, backlog 19 `## 결과` |

- 두 병원 약관은 사전 승낙 없는 영리목적 이용과 제3자 이용을 막는다(서울대병원과 같은 조건)
- 인제대 백병원 질병백과는 약관이 개인 이용 외의 복사·가공·배포를 막아 넣지 않았다(사용자 결정, 2026-11-17)
- 식별 정보: 없음. 질환 안내 페이지의 진료과 칸만 적었다

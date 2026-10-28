# 데이터 출처

원본은 `data/raw/<출처>/`에 받은 바이트 그대로 둔다(git 제외). 내려받기와 검증:

```sh
uv run python scripts/download_data.py           # 없거나 해시가 다른 파일만 내려받은 뒤 검증
uv run python scripts/download_data.py --verify  # 내려받지 않고 해시만 검증
```

해시는 `src/fornav_modeling/data/download.py`에 고정돼 있고, 이 문서의 sha256과 같아야 한다(`tests/test_download.py`가 확인한다). 출처가 파일을 바꿔 검증이 실패하면 새 파일을 확인한 뒤 두 곳을 함께 고친다.

확인 날짜는 모두 **2026-10-27**이다.

## 요약

| 폴더 | 용도 | 출처 | 라이선스 | 학습·평가 사용 |
|---|---|---|---|---|
| `kaggle_triage/` | 응급도 모델 | PLOS ONE 논문 S1 Appendix (Kaggle "Emergency Service – Triage Application"의 원 출처) | CC BY 4.0 | 가능. 출처 표시 필요, 상업 이용 가능 |
| `kaggle_symptom/` | 진료과 모델 A | Kaggle "Disease Symptom Prediction" | CC BY-SA 4.0 | 가능. 출처 표시 필요, 상업 이용 가능. 가공한 데이터를 배포하면 같은 라이선스(동일조건변경허락) |
| `hira/` | 질환 → 진료과 매핑, 모델 B 라벨 | 공공데이터포털, 건강보험심사평가원 | 공공누리 제1유형(출처표시) | 가능. 출처 표시 필요, 상업 이용·변경 가능 |

식별 정보(이름·연락처·기관명) 열은 세 출처 모두 **없음**. 가공 단계에서 지울 열도 없다. 아래 출처별 "식별 정보" 항목에 점검 내용을 적었다.

## kaggle_triage — 응급도

- 데이터: Moon S-H, Shim JL, Park K-S, Park C-S (2019) Triage accuracy and causes of mistriage using the Korean Triage and Acuity Scale. *PLoS ONE* 14(9): e0216972. https://doi.org/10.1371/journal.pone.0216972 — S1 Appendix "EMR review coding data"
- 내려받는 URL: https://journals.plos.org/plosone/article/file?type=supplementary&id=10.1371/journal.pone.0216972.s001
- 라이선스: CC BY 4.0. 논문 페이지에 "open access article distributed under the terms of the Creative Commons Attribution License"로 표시돼 있고, Data Availability가 "All relevant data are within the paper and its Supporting Information files"라 S1 Appendix도 같은 조건이다
- **Kaggle 판을 쓰지 않는 이유**: Kaggle 판(https://www.kaggle.com/datasets/ilkeryildiz/emergency-service-triage-application, v2)은 라이선스가 "Other (specified in description)"인데 설명에 라이선스 문구가 없다. 내용은 이 S1 Appendix를 옮긴 것이다(1,267행 × 24열, 열 이름 같음. Kaggle 판은 `Age` 등을 반올림하고 latin-1/cp1252 CSV로 저장됨). 라이선스가 표시된 원본을 쓰기로 했다(2026-10-27 사용자 결정)

| 파일 | sha256 | 행 | 형식 |
|---|---|---|---|
| `pone.0216972.s001.xlsx` | `f631c951178799179d0fbd74fe979464b955ea1b426222bf015b163b8a24beb0` | 1,267 (+머리글) | xlsx, 시트 1개 `N=1267 data` |

- 열(24): `Group`, `Sex`, `Age`, `Patients number per hour`, `Arrival mode`, `Injury`, `Chief_complain`, `Mental`, `Pain`, `NRS_pain`, `SBP`, `DBP`, `HR`, `RR`, `BT`, `Saturation`, `KTAS_RN`, `Diagnosis in ED`, `Disposition`, `KTAS_expert`, `Error_group`, `Length of stay_min`, `KTAS duration_min`, `mistriage`
- 코드값(Kaggle 판 설명 기준): `Sex` 1=여 2=남, `Injury` 1=아니오 2=예, `Pain` 1=있음 0=없음, `Mental` 1=Alert 2=Verbal 3=Pain 4=Unresponsive, `Group` 1=지역응급의료기관 2=권역응급의료센터
- `KTAS_expert`(전문가가 정한 KTAS) 분포: 1=26, 2=220, 3=487, 4=459, 5=75 (합 1,267)
- 참고: 활력징후 열(`SBP`~`Saturation`)에 문자열 `측불`(측정 불가)이 섞여 있다(`SBP` 25건 등). `NRS_pain` 빈칸 556건, `Diagnosis in ED` 빈칸 2건. `Chief_complain`은 영어·한국어 자유 텍스트(고유값 427개)
- 식별 정보: 없음. 이름·연락처·병원명 열이 없고, `Group`은 응급실 종별 코드다. 자유 텍스트 열(`Chief_complain`, `Diagnosis in ED`)에서 이메일(`@`)·전화번호 형태(숫자 3자리 이상)를 찾았고, 나온 것은 상병코드 `S376` 1건뿐이다

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

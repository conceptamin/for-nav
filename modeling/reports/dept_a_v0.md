# dept_a_v0

진료과 Top-k 적중률(분자/분모)

| 모델·평가셋 | Top-1 | Top-2 |
|---|---|---|
| LightGBM valid(Kaggle) | 40/44 (90.9%) | 42/44 (95.5%) |
| 기준선: train 질환 빈도 valid(Kaggle) | 26/44 (59.1%) | 31/44 (70.5%) |
| LightGBM train+valid 3겹 교차검증 | 221/233 (94.8%) | 226/233 (97.0%) |
| LightGBM 진료과 검증셋(guide) | 5/29 (17.2%) | 10/29 (34.5%) |

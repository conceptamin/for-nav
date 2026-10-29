# experiment_vitals

버튼 피처만 쓴 응급도 LightGBM과 버튼 + 활력징후 LightGBM. 같은 분할·seed·설정, 검증셋 비교(test 미사용). 서빙 모델과 무관하다.

| 모델·규칙 | emergency 재현율 | today 재현율 | outpatient 재현율 | emergency 정밀도 | today 정밀도 | outpatient 정밀도 | 정확도 |
|---|---|---|---|---|---|---|---|
| buttons valid (argmax) | 25/37 (67.6%) | 47/73 (64.4%) | 66/80 (82.5%) | 25/34 (73.5%) | 47/69 (68.1%) | 66/87 (75.9%) | 138/190 (72.6%) |
| buttons valid (threshold) | 36/37 (97.3%) | 26/73 (35.6%) | 50/80 (62.5%) | 36/99 (36.4%) | 26/31 (83.9%) | 50/60 (83.3%) | 112/190 (59.0%) |
| buttons_vitals valid (argmax) | 23/37 (62.2%) | 49/73 (67.1%) | 61/80 (76.2%) | 23/34 (67.7%) | 49/69 (71.0%) | 61/87 (70.1%) | 133/190 (70.0%) |
| buttons_vitals valid (threshold) | 36/37 (97.3%) | 16/73 (21.9%) | 42/80 (52.5%) | 36/124 (29.0%) | 16/18 (88.9%) | 42/48 (87.5%) | 94/190 (49.5%) |
| buttons cv_train_valid (argmax) | 119/197 (60.4%) | 270/389 (69.4%) | 349/427 (81.7%) | 119/165 (72.1%) | 270/379 (71.2%) | 349/469 (74.4%) | 738/1013 (72.9%) |
| buttons cv_train_valid (threshold) | 184/197 (93.4%) | 156/389 (40.1%) | 276/427 (64.6%) | 184/500 (36.8%) | 156/190 (82.1%) | 276/323 (85.5%) | 616/1013 (60.8%) |
| buttons_vitals cv_train_valid (argmax) | 128/197 (65.0%) | 270/389 (69.4%) | 339/427 (79.4%) | 128/171 (74.9%) | 270/398 (67.8%) | 339/444 (76.3%) | 737/1013 (72.8%) |
| buttons_vitals cv_train_valid (threshold) | 190/197 (96.5%) | 120/389 (30.9%) | 244/427 (57.1%) | 190/588 (32.3%) | 120/150 (80.0%) | 244/275 (88.7%) | 554/1013 (54.7%) |

임계값(valid 응급 재현율 ≥ 95% 중 정밀도 최대)

| 설정 | 임계값 | valid 응급 재현율 | valid 응급 예측 건수 | 학습 라운드 |
|---|---|---|---|---|
| buttons | 0.0738 | 36/37 | 99/190 | 86 |
| buttons_vitals | 0.0500 | 36/37 | 124/190 | 69 |

활력징후 결측(분자/분모)

| 피처 | train | valid |
|---|---|---|
| sbp | 11/823 | 10/190 |
| dbp | 15/823 | 10/190 |
| hr | 8/823 | 8/190 |
| rr | 10/823 | 6/190 |
| bt | 9/823 | 5/190 |
| saturation | 446/823 | 112/190 |

SHAP(valid, 클래스별 평균 |SHAP| 상위 피처, 원점수 단위)

## buttons

| 클래스 | 활력징후 몫 | 상위 피처 |
|---|---|---|
| emergency | - | body_chest 0.386, age_group 0.358, pain_score 0.297, mental 0.223, sex_male 0.116, symptom_cantmove 0.096, symptom_pain 0.072, body_head 0.063 |
| today | - | pain_score 0.291, body_abdomen 0.226, symptom_pain 0.210, injury 0.192, symptom_dizzy 0.144, mental 0.135, age_group 0.129, sex_male 0.092 |
| outpatient | - | body_chest 0.595, pain_score 0.452, body_abdomen 0.144, symptom_pain 0.129, symptom_dizzy 0.117, age_group 0.099, symptom_cut 0.089, symptom_bleeding 0.087 |

## buttons_vitals

| 클래스 | 활력징후 몫 | 상위 피처 |
|---|---|---|
| emergency | 43.3% | body_chest 0.310, age_group 0.266, sbp 0.245, saturation 0.205, hr 0.184, pain_score 0.160, mental 0.146, bt 0.145 |
| today | 26.3% | pain_score 0.242, body_abdomen 0.190, symptom_dizzy 0.170, symptom_pain 0.139, bt 0.119, injury 0.112, dbp 0.096, sbp 0.079 |
| outpatient | 25.8% | body_chest 0.491, pain_score 0.385, saturation 0.161, hr 0.115, body_abdomen 0.115, injury 0.099, symptom_pain 0.099, bt 0.098 |

그림: `figures/experiment_vitals_confusion.png`(임계값 규칙 혼동행렬), `figures/experiment_vitals_recall.png`(클래스별 재현율)

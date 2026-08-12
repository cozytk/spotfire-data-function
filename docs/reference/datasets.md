---
title: 실습 데이터셋 안내
parent: 참고 자료
nav_order: 3
---

# 실습 데이터셋 안내
{: .no_toc }

모든 데이터는 [`data/` 폴더](https://github.com/cozytk/spotfire-data-function/tree/main/data)에 있습니다.
{: .fs-5 .fw-300 }

{: .주의 }
> **사내 실제 데이터가 아닙니다.**
> `titanic` / `iris` / `diabetes` 는 공개 데이터셋이고,
> 나머지는 교육용으로 만든 **가상 데이터**입니다
> ([생성 스크립트](https://github.com/cozytk/spotfire-data-function/blob/main/scripts/make_datasets.py)).
> 값의 분포와 컬럼 구성은 실무와 비슷하게 설계했지만, 실제 공정 수치와는 무관합니다.

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## fab_measurement.csv — 공정 계측 이력

**11,091행 × 15컬럼.** 이 교안의 주력 데이터입니다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `LOT_ID` / `JOIN_ID` | 문자열 | LOT 번호 (`JOIN_ID` 는 조인 실습용 동일 값) |
| `WAFER_NO` | 정수 | 웨이퍼 번호 1~25 |
| `STEP_DESC` | 문자열 | 공정 `PC`, `RMG`, `CBCMP`, `ETCH`, `PHOTO` |
| `EQP_ID` | 문자열 | 설비 (`PC01`, `ETC01`, `CMP02` …) |
| `CHAMBER` | 문자열 | 챔버 `A`/`B`/`C` |
| `MEAS_TIME` | 문자열 | 계측 시각 `YYYY-MM-DD HH:MM:SS` |
| `THICKNESS` | 실수 | 두께 (공정별 목표값 상이) |
| `CD` | 실수 | 임계 치수 |
| `TEMP` / `PRESSURE` | 실수 | 온도 / 압력 |
| `PARTICLE_CNT` | 정수 | 파티클 수 (**0이 정상값**) |
| `SIZE_Y` | 실수 | 결함 크기 |
| `IS_DEFECT` | 문자열 | `REAL` / `FALSE` (값이 정리되지 않은 상태) |
| `OPER_ID` | 문자열 | 작업자 ID |

### 일부러 심어 둔 문제들

| 문제 | 규모 | 관련 예제 |
|---|---|---|
| 완전 중복 행 (재전송) | 약 3% | 01 |
| 재측정 행 (같은 키, 다른 시각) | 약 2% | 01 |
| 결측 (`CD`, `TEMP`, `THICKNESS`, `SIZE_Y`) | 2~5% | 02, 08 |
| `PRESSURE = 0` (센서 미취득) | 약 1.5% | 02 |
| 이상치 스파이크 (두께 15~40% 상승) | 약 1.2% | 11, 12 |
| 설비별 드리프트 | 설비마다 상이 | 13 |
| `IS_DEFECT` 값 불일치 (`REAL`) | 전체 | 03, 06 |

---

## lot_master.csv — LOT 마스터

**120행.** 조인 실습용.

`LOT_ID`, `JOIN_ID`, `PRODUCT`, `LINE`, `PRIORITY`(HOT/NORMAL/LOW), `PLAN_QTY`, `START_TIME`, `OWNER_DEPT`

---

## equipment_sensor_wide.csv — 설비 센서 (Wide)

**1,344행 × 22컬럼.** 4개 설비 × 7일 × 30분 간격.

`TIMESTAMP`, `EQP_ID`(ETC01/ETC02/CMP01/CMP02), `S001` ~ `S020`

- 센서별 결측 약 1% (통신 유실)
- **Wide → Long 변환**(05), **상관 분석**(17), **시간 근접 조인**(14)에 사용

---

## equipment_alarm_log.csv — 설비 알람 로그

**900행.** 텍스트 파싱과 세션화 실습용.

| 컬럼 | 설명 |
|---|---|
| `EQP_ID` | 설비 |
| `ALARM_TIME` | 발생 시각 (불규칙 간격) |
| `SEVERITY` | `INFO` / `WARN` / `ERROR` |
| `MESSAGE` | `[E-1023] Chamber pressure high (LOT=L26043, STEP=ETCH, value=12.34 unit)` |
| `RECIPE` | 레시피명 |
| `ACK_BY` | 확인자 (빈 값 있음) |

---

## wafer_yield.csv — 웨이퍼 수율

**3,000행.** 파레토·ABC 분석 실습용.

`LOT_ID`, `WAFER_NO`, `PRODUCT`, `LINE`, `TOTAL_DIE`, `GOOD_DIE`, `YIELD_PCT`, `MAIN_FAIL_TYPE`, `TEST_DATE`

불량 유형 8종(`PARTICLE`, `BRIDGE`, `OPEN`, `SCRATCH`, `MISALIGN`, `THIN_FILM`, `EDGE_CHIP`, `ETC`)이
**파레토 분포**를 이루도록 만들었습니다.

---

## hr_training.csv — 임직원 교육 이수 현황

**1,400행.** 공정 데이터가 아닌 업무에서도 같은 기술이 쓰인다는 것을 보여 주는 데이터입니다.

`EMP_ID`, `DEPT`, `JOB_ROLE`, `GRADE`, `COURSE`, `CATEGORY`, `PLAN_HOURS`, `DONE_HOURS`, `SCORE`(결측 12%), `COMPLETED_DATE`

- 피벗/크로스탭(06), 그룹 집계(07) 실습에 사용
- 부서 × 카테고리 이수율 매트릭스, 직무별 평균 점수 등

---

## sales_orders.csv — 제품 수주/출하

**1,600행.** 영업·SCM 직무 관점의 데이터입니다.

`ORDER_ID`, `ORDER_DATE`, `CUSTOMER`(40개사), `REGION`, `PRODUCT_FAMILY`,
`QTY`, `UNIT_PRICE_USD`, `AMOUNT_USD`, `PROMISE_DATE`, `SHIP_DATE`(빈 값 있음), `STATUS`

- ABC/파레토 분석(19), 시계열 재집계(09 응용)
- `PROMISE_DATE` 와 `SHIP_DATE` 차이로 **납기 준수율** 계산 가능

---

## 공개 데이터셋

### titanic.csv (891행)

`PassengerId`, `Survived`, `Pclass`, `Name`, `Sex`, `Age`(결측 20%), `SibSp`, `Parch`,
`Ticket`, `Fare`, `Cabin`(결측 77%), `Embarked`

전처리 종합 실습(결측 대치, 정규식 파생, 구간화, 원-핫 인코딩)에 사용.

### iris.csv (150행)

`sepal_length`, `sepal_width`, `petal_length`, `petal_width`, `species`

그룹 통계·판별 규칙·클러스터링 검증에 사용. 결측 없음.

### diabetes_train.csv (614행) / diabetes_test.csv (154행)

Pima 인디언 당뇨 데이터. 8:2로 분할해 두었습니다.

`Pregnancies`, `Glucose`, `BloodPressure`, `SkinThickness`, `Insulin`, `BMI`,
`DiabetesPedigreeFunction`, `Age`, `Outcome`

{: .팁 }
> **`Glucose`, `BloodPressure`, `SkinThickness`, `Insulin`, `BMI` 의 0은 결측입니다.**
> 살아 있는 사람의 혈당이 0일 수 없습니다.
> "센서 미취득이 0으로 기록되는" 현장 상황과 정확히 같은 문제라서,
> 이 교안에서 가장 중요한 교육 포인트 중 하나입니다. ([24번 예제](../../examples/24-public-datasets/))

---

## Spotfire에 불러오기

1. **파일 > 열기 > 데이터 원본 없이 시작** 또는 기존 분석 열기
2. **파일 > 데이터 추가 > 로컬 파일** 에서 CSV 선택
3. 인코딩이 깨지면 **UTF-8** 로 지정 (CSV는 `utf-8-sig` 로 저장되어 있습니다)
4. `MEAS_TIME` 등 시각 컬럼은 **문자열로 두어도 무방**합니다.
   데이터 함수 안에서 `pd.to_datetime()` 으로 변환하는 연습이 포함되어 있습니다.

## 데이터 재생성

값을 바꾸거나 규모를 키우고 싶다면:

```bash
python scripts/make_datasets.py
```

난수 시드가 고정되어 있어 **매번 같은 데이터**가 생성됩니다.
행 수를 늘리려면 스크립트의 `n_lot`, `n` 파라미터를 조정하세요.

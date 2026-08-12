---
title: 14. 시간 근접 조인 (merge_asof) — 계측 시점의 설비 상태 붙이기
parent: 예제 모음
nav_order: 14
---

# 14. 시간 근접 조인 (merge_asof) — 계측 시점의 설비 상태 붙이기
{: .no_toc }

**난이도** ★★★ · **Level 3 · 시계열과 공정 분석**

키가 정확히 일치하지 않는 두 시계열을 "가장 가까운 직전 값" 기준으로 조인합니다. Spotfire 기본 기능으로는 불가능에 가까운 작업.

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv), [`equipment_sensor_wide.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/equipment_sensor_wide.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/14_merge_asof.py)

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

### 파라미터 요약
{: .no_toc }

| 구분 | 이름 | 타입 | 연결 |
|---|---|---|---|
| 입력 | `input1` | Table | `fab_measurement.csv` |
| 입력 | `input2` | Table | `equipment_sensor_wide.csv` |
| 입력 | `tolerance_min` | Value | 문서 속성 (예: `60`) |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_stats` | Table | 새 데이터 테이블 |

---

## 시나리오

- 계측 데이터는 **웨이퍼를 측정한 시각**에 찍힙니다 (불규칙).
- 센서 데이터는 **30분마다** 찍힙니다 (규칙적).
- 두 시각은 **절대 정확히 일치하지 않습니다.**

"이 웨이퍼를 측정할 당시 챔버 온도는 얼마였나?" 에 답하려면
**계측 시각 직전의 가장 가까운 센서값**을 붙여야 합니다. 이것이 `merge_asof` 입니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire의 조인은 **정확히 일치하는 키**만 지원합니다. `=` 조인뿐입니다.
- 시각을 시간 단위로 반올림해서 조인하는 우회법이 있지만
  - 경계에서 틀리고 (11:59 계측이 12:00 센서값과 매칭),
  - 센서 주기가 불규칙하면 아예 매칭이 안 되며,
  - **"몇 분 이내만 유효"** 라는 허용 오차를 표현할 수 없습니다.
- `merge_asof` 는 이 모든 것을 인자 하나씩으로 처리합니다. **데이터 함수를 도입할 이유 그 자체**인 기능입니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input1` | Table | `fab_measurement` (계측) |
| 입력 | `input2` | Table | `equipment_sensor_wide` (센서) |
| 입력 | `tolerance_min` | Value (Integer) | 문서 속성 `ToleranceMin` — 허용 시간차(분) |
| 출력 | `output` | Table | 센서값이 붙은 계측 데이터 |
| 출력 | `output_stats` | Table | 매칭 성공률 요약 |

## 스크립트

```python
import numpy as np
import pandas as pd

meas = input1.copy()
sensor = input2.copy()

SENSOR_COLS = ["S001", "S002", "S003", "S004", "S005"]

meas["MEAS_TIME"] = pd.to_datetime(meas["MEAS_TIME"])
sensor["TIMESTAMP"] = pd.to_datetime(sensor["TIMESTAMP"])

# 전제조건 ① by 컬럼의 dtype 을 양쪽에서 동일하게 (다르면 매칭이 조용히 0건이 된다)
meas["EQP_ID"] = meas["EQP_ID"].astype(str).str.strip().str.upper()
sensor["EQP_ID"] = sensor["EQP_ID"].astype(str).str.strip().str.upper()

# 전제조건 ② 양쪽 모두 조인 키(시간)로 정렬 — 정렬하지 않으면 ValueError
meas = meas.sort_values("MEAS_TIME").reset_index(drop=True)
sensor = sensor.sort_values("TIMESTAMP").reset_index(drop=True)

right = sensor[["TIMESTAMP", "EQP_ID"] + SENSOR_COLS].copy()
right["SENSOR_TIME"] = right["TIMESTAMP"]

merged = pd.merge_asof(
    meas,
    right,
    left_on="MEAS_TIME",
    right_on="TIMESTAMP",
    by="EQP_ID",                                  # 전제조건 ③ 설비별로 따로 매칭
    direction="backward",                         # 계측 '이전'의 가장 가까운 센서값
    tolerance=pd.Timedelta(minutes=int(tolerance_min)),
)

merged["LAG_MIN"] = (merged["MEAS_TIME"] - merged["SENSOR_TIME"]).dt.total_seconds() / 60
merged["MATCHED"] = merged["SENSOR_TIME"].notna()
merged = merged.drop(columns=["TIMESTAMP"])

# 매칭 성공률 — '조용한 실패'를 잡아내는 안전장치
stats = (
    merged.groupby("EQP_ID", as_index=False)
    .agg(N=("MATCHED", "size"), MATCHED_N=("MATCHED", "sum"), LAG_MEAN=("LAG_MIN", "mean"), LAG_MAX=("LAG_MIN", "max"))
)
stats["MATCH_PCT"] = (stats["MATCHED_N"] / stats["N"] * 100).round(2)
stats[["LAG_MEAN", "LAG_MAX"]] = stats[["LAG_MEAN", "LAG_MAX"]].round(2)
stats["NOTE"] = np.where(stats["MATCH_PCT"] == 0, "센서 데이터 없음(설비 범위 확인)", "")

merged["LAG_MIN"] = merged["LAG_MIN"].round(2)

output = merged
output_stats = stats
```

## 핵심 포인트

`merge_asof` 를 쓸 때 반드시 지켜야 하는 3가지가 있습니다. 하나라도 어기면 오류가 나거나 조용히 틀립니다.

1. **양쪽 모두 조인 키(시간)로 정렬**되어 있어야 합니다. 안 그러면 `ValueError` 가 납니다.
2. **`by=` 로 그룹을 지정**하세요. 설비 ETC01의 계측에 CMP01 센서값이 붙으면 안 됩니다.
3. **`tolerance` 를 반드시 지정**하세요. 없으면 3일 전 센서값이 붙어도 매칭으로 처리됩니다.
   `direction="backward"`(기본)는 "계측 시각 **이전**의 가장 가까운 값"입니다.
   `"nearest"` 는 앞뒤 상관없이 가장 가까운 값이며, 미래 값을 끌어오면 안 되는
   분석(예: 예측 모델 학습 데이터)에서는 반드시 `backward` 를 쓰세요.

> `by` 컬럼의 dtype이 양쪽에서 다르면(예: 한쪽은 문자열, 한쪽은 범주형) 매칭이 0건이 됩니다.
> **매칭률을 항상 함께 출력**해서 조용한 실패를 잡아내세요.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. pandas.merge_asof 를 사용해줘.
입력: input1(계측: LOT_ID, WAFER_NO, EQP_ID, STEP_DESC, MEAS_TIME, THICKNESS)
      input2(센서: TIMESTAMP, EQP_ID, S001~S020)
      tolerance_min(int, 허용 시간차 분)
요구사항:
1. 각 계측 행에 대해, 같은 EQP_ID 의 센서 데이터 중 MEAS_TIME '이전'의 가장 가까운 행을 붙여줘
2. 시간차가 tolerance_min 분을 넘으면 매칭하지 말 것
3. 실제 붙은 센서 시각과 시간차(분)를 SENSOR_TIME, LAG_MIN 컬럼으로 남겨줘
4. 센서는 S001~S005 만 붙이고, 매칭 안 된 행도 삭제하지 말고 NaN 으로 남겨줘
5. EQP_ID 별 매칭 성공률(%) 요약 테이블도 만들어줘
merge_asof 의 전제조건(양쪽 시간 정렬, by 지정, dtype 일치)을 코드에 반영하고
주석으로 이유를 설명해줘. 출력은 output, output_stats.
```

## 확인 & 응용

- `LAG_MIN` 의 분포를 히스토그램으로 보세요. 값이 지나치게 크면 센서 수집이 끊긴 구간입니다.
- **응용**: `direction="nearest"` 로 바꿔 매칭률 변화를 비교해 보세요.
- **응용**: 붙인 센서값과 `THICKNESS` 의 상관을 계산하면([17번](../17-correlation-pairs/))
  "어떤 센서가 두께에 영향을 주는가"를 데이터로 답할 수 있습니다.

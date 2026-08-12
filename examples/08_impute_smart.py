'''---
title: 결측치를 "지우지 않고" 똑똑하게 채우기
level: 2
difficulty: ★★☆
summary: 그룹 중앙값 대치, 시간 기반 선형 보간, 앞/뒤 값 채움을 컬럼 성격에 맞게 골라 적용하고, 무엇을 채웠는지 흔적을 남깁니다.
data: [fab_measurement.csv]
inputs:
  input:
    file: fab_measurement.csv
  max_gap: 3
outputs: [output, output_report]
---
## 시나리오

계측 결측을 전부 지우면 데이터의 상당 부분이 날아갑니다. 컬럼 성격에 따라 처리를 달리해야 합니다.

| 컬럼 | 성격 | 적절한 처리 |
|---|---|---|
| `THICKNESS`, `CD` | 공정 조건에 종속 | **같은 설비·공정 그룹의 중앙값**으로 대치 |
| `TEMP` | 시간에 따라 연속적으로 변함 | **시간 기반 선형 보간** (단, 긴 공백은 채우지 않음) |
| `CHAMBER` | 범주형, 잘 안 변함 | **직전 값으로 채움**(ffill) |

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire의 "값 바꾸기"는 **상수 대치** 수준입니다. 그룹별 중앙값 대치는 계산 컬럼으로 흉내 내야 하고,
  결과가 원본 컬럼을 대체하지 않아 컬럼이 두 벌로 늘어납니다.
- **시간 기반 보간**은 기본 기능으로 사실상 불가능합니다.
- "3칸 이상 연속 결측은 채우지 않는다" 같은 **실무적인 안전장치**를 표현할 방법이 없습니다.
- 데이터 함수는 대치 방법·한도·흔적 컬럼을 모두 코드로 명시할 수 있습니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 입력 | `max_gap` | Value (Integer) | 문서 속성 `MaxGap` — 연속 보간 허용 칸 수 |
| 출력 | `output` | Table | 대치 완료 데이터 (`*_IMPUTED` 플래그 포함) |
| 출력 | `output_report` | Table | 컬럼별 대치 건수 리포트 |

## 스크립트

{{CODE}}

## 핵심 포인트

- **대치했다는 사실을 반드시 남기세요.** `_IMPUTED` 불리언 컬럼 하나면 충분하고,
  나중에 "이 값 진짜예요?"라는 질문에 즉답할 수 있습니다. 실무 신뢰도가 완전히 달라집니다.
- `groupby(...)[col].transform(lambda s: s.fillna(s.median()))` 이 그룹 중앙값 대치의 정석입니다.
- 시간 보간은 **인덱스를 시간으로 설정**한 뒤 `interpolate(method="time")` 을 씁니다.
  `limit=max_gap` 으로 긴 공백을 방치하면, 없는 데이터를 만들어 내는 사고를 막을 수 있습니다.
- 범주형은 보간하면 안 됩니다. `ffill()` → `bfill()` 순서로 채우고, 그래도 남으면 `"UNKNOWN"`.
- 그룹 전체가 결측이면 중앙값도 `NaN` 입니다. **전체 중앙값으로 한 번 더 받쳐 주세요.**

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input(DataFrame), max_gap(int).
컬럼별로 결측 처리 방식을 다르게 적용해줘.
- THICKNESS, CD : (EQP_ID, STEP_DESC) 그룹의 중앙값으로 대치. 그룹 전체가 결측이면 전체 중앙값 사용
- TEMP : EQP_ID 별로 MEAS_TIME 기준 시간 선형 보간, 단 연속 결측이 max_gap 칸을 넘으면 채우지 않음
- CHAMBER : EQP_ID 별 직전 값(ffill) -> 이후 값(bfill) -> 그래도 없으면 'UNKNOWN'
각 컬럼마다 <컬럼명>_IMPUTED 불리언 컬럼을 만들어 대치 여부를 표시하고,
컬럼별 대치 건수/대치율 리포트도 output_report 로 내보내줘.
```

## 확인 & 응용

- `output_report` 의 대치율이 20%를 넘는 컬럼이 있다면 **대치보다 원인 규명이 먼저**입니다.
- **응용**: `diabetes_train.csv` 는 `Glucose`, `BloodPressure`, `BMI` 의 **0이 사실상 결측**입니다.
  0을 `NaN` 으로 바꾼 뒤 `Outcome` 그룹별 중앙값으로 대치해 보세요. 실전 감각을 익히기 좋은 과제입니다.
'''
import numpy as np
import pandas as pd

df = input.copy()
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])
df = df.sort_values(["EQP_ID", "MEAS_TIME"]).reset_index(drop=True)

report = []


def mark(col):
    """대치 전 결측 위치를 기록해 두는 헬퍼."""
    df[col + "_IMPUTED"] = df[col].isna()
    return df[col].isna().sum()


# 1) 공정 조건 종속 컬럼 : 그룹 중앙값 대치
for col in ["THICKNESS", "CD"]:
    n_missing = mark(col)
    grp_median = df.groupby(["EQP_ID", "STEP_DESC"])[col].transform("median")
    df[col] = df[col].fillna(grp_median)
    df[col] = df[col].fillna(df[col].median())  # 그룹 전체가 결측인 경우의 안전망
    report.append({"COLUMN": col, "METHOD": "그룹 중앙값", "MISSING": int(n_missing)})

# 2) 시간에 따라 연속적인 컬럼 : 시간 기반 선형 보간 (긴 공백은 그대로 둔다)
col = "TEMP"
n_missing = mark(col)
filled = []
for eqp, block in df.groupby("EQP_ID", sort=False):
    s = block.set_index("MEAS_TIME")[col].interpolate(method="time", limit=int(max_gap), limit_direction="both")
    filled.append(pd.Series(s.to_numpy(), index=block.index))
df[col] = pd.concat(filled).sort_index()
report.append({"COLUMN": col, "METHOD": f"시간 보간(limit={max_gap})", "MISSING": int(n_missing)})

# 3) 범주형 : 앞 -> 뒤 -> UNKNOWN
col = "CHAMBER"
n_missing = mark(col)
df[col] = df.groupby("EQP_ID")[col].ffill()
df[col] = df.groupby("EQP_ID")[col].bfill()
df[col] = df[col].fillna("UNKNOWN")
report.append({"COLUMN": col, "METHOD": "ffill -> bfill -> UNKNOWN", "MISSING": int(n_missing)})

rep = pd.DataFrame(report)
rep["REMAIN_MISSING"] = [int(df[c].isna().sum()) for c in rep["COLUMN"]]
rep["IMPUTED"] = rep["MISSING"] - rep["REMAIN_MISSING"]
rep["IMPUTE_PCT"] = (rep["IMPUTED"] / len(df) * 100).round(2)

output = df
output_report = rep

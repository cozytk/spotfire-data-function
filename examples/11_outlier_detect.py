'''---
title: 이상치 탐지 4종 비교 (IQR / Z / MAD / Hampel)
level: 3
difficulty: ★★★
summary: 같은 데이터에 네 가지 이상치 기준을 동시에 적용해 결과를 비교하고, 몇 개 기준에서 걸렸는지로 신뢰도를 매깁니다.
data: [fab_measurement.csv]
inputs:
  input:
    file: fab_measurement.csv
  k_sigma: 3.0
outputs: [output, output_summary]
---
## 시나리오

"이상치를 찾아 달라"는 요청에는 함정이 있습니다. **이상치의 정의가 하나가 아니기** 때문입니다.

| 방법 | 기준 | 특징 |
|---|---|---|
| IQR | Q1-1.5×IQR ~ Q3+1.5×IQR 밖 | 분포 가정 없음, 박스플롯과 동일 |
| Z-score | \|z\| > 3 | 정규분포 가정, **이상치 자신이 평균·표준편차를 오염** |
| MAD | 중앙값 기반 로버스트 z > 3.5 | 오염에 강함, 소량 이상치에 적합 |
| Hampel | 이동 중앙값 기준 이탈 | **트렌드가 있는 시계열**에 적합 |

정답은 "여러 개를 같이 보고 **몇 개에서 동시에 걸렸는지**로 판단하는 것"입니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- 박스플롯이 IQR 기준 이상치를 **그려 주기는** 합니다. 그러나 그 결과를 **컬럼(데이터)으로 받을 수 없습니다.**
- Z-score는 OVER 표현식으로 가능하지만, **MAD와 Hampel은 중앙값 기반 이동 통계**라 표현식으로 만들 수 없습니다.
- 네 기준을 나란히 두고 비교하는 표를 만드는 것은 기본 기능으로는 사실상 불가능합니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 입력 | `k_sigma` | Value (Real) | 문서 속성 `KSigma` (기본 3.0) |
| 출력 | `output` | Table | 원본 + 방법별 이상치 플래그 |
| 출력 | `output_summary` | Table | 방법별 검출 건수 비교 |

## 스크립트

{{CODE}}

## 핵심 포인트

- **`quantile()` 로 IQR**, **`median()`+MAD 로 로버스트 z**, **`rolling().median()` 으로 Hampel**.
  전부 pandas 기본 기능이며 각각 두세 줄입니다.
- Hampel 필터의 `1.4826` 은 MAD를 정규분포의 표준편차와 같은 스케일로 맞추는 상수입니다.
  (`0.6745` 는 그 역수 계열 상수로, 로버스트 z에 쓰입니다.)
- **`VOTES` (몇 개 기준에서 걸렸는가)** 컬럼이 이 예제의 핵심 산출물입니다.
  4개 중 3개 이상이면 거의 확실한 이상치, 1개면 방법 특성일 가능성이 큽니다.
- 이상치는 **지우기 전에 원인을 보세요.** 설비 이상의 증거일 수도, 진짜 불량일 수도 있습니다.
  그래서 이 예제는 행을 지우지 않고 **플래그만** 붙입니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input(DataFrame), k_sigma(float).
대상 값 THICKNESS, 그룹 키 (EQP_ID, STEP_DESC), 시간 컬럼 MEAS_TIME.
그룹별로 아래 4가지 이상치 플래그를 만들어줘 (원본 행 수 유지):
1. OUT_IQR    : Q1-1.5*IQR ~ Q3+1.5*IQR 밖
2. OUT_Z      : |z| > k_sigma
3. OUT_MAD    : 0.6745*(x-median)/MAD 의 절대값 > 3.5
4. OUT_HAMPEL : 창 크기 11 이동중앙값 기준, |x-이동중앙값| > 3*1.4826*이동MAD
그리고 VOTES(=4개 중 걸린 개수)와 OUTLIER_LEVEL('확실'>=3, '의심'2, '경미'1, '정상'0) 컬럼 추가.
0으로 나누는 경우, 표본이 창 크기보다 적은 그룹을 방어해줘.
방법별 검출 건수/비율 요약도 output_summary 로 출력.
행은 삭제하지 말고 플래그만 붙일 것.
```

## 확인 & 응용

- `VOTES` 를 색으로 칠한 산점도를 그려 보세요. 4표짜리 점들이 특정 시간대에 몰려 있다면 설비 이벤트입니다.
- **응용**: `titanic.csv` 의 `Fare` 에 같은 코드를 돌려 보세요. 한쪽으로 심하게 치우친 분포에서는
  IQR과 Z-score의 결과가 크게 달라진다는 걸 확인할 수 있습니다.
'''
import numpy as np
import pandas as pd

df = input.copy()
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])
df = df.sort_values(["EQP_ID", "STEP_DESC", "MEAS_TIME"]).reset_index(drop=True)

GROUP = ["EQP_ID", "STEP_DESC"]
VALUE = "THICKNESS"
HAMPEL_WINDOW = 11

g = df.groupby(GROUP)[VALUE]
x = df[VALUE]

# 1) IQR 기준
q1 = g.transform(lambda s: s.quantile(0.25))
q3 = g.transform(lambda s: s.quantile(0.75))
iqr = (q3 - q1).replace(0, np.nan)
df["OUT_IQR"] = (x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)

# 2) 표준 Z-score 기준
mean = g.transform("mean")
std = g.transform("std").replace(0, np.nan)
df["Z"] = (x - mean) / std
df["OUT_Z"] = df["Z"].abs() > float(k_sigma)

# 3) MAD 기반 로버스트 Z (이상치에 오염되지 않음)
med = g.transform("median")
mad = g.transform(lambda s: (s - s.median()).abs().median()).replace(0, np.nan)
df["ROBUST_Z"] = 0.6745 * (x - med) / mad
df["OUT_MAD"] = df["ROBUST_Z"].abs() > 3.5

# 4) Hampel 필터 : 이동 중앙값 기준 (트렌드가 있어도 잘 동작)
roll_med = g.transform(lambda s: s.rolling(HAMPEL_WINDOW, center=True, min_periods=3).median())
roll_mad = g.transform(
    lambda s: (s - s.rolling(HAMPEL_WINDOW, center=True, min_periods=3).median())
    .abs()
    .rolling(HAMPEL_WINDOW, center=True, min_periods=3)
    .median()
)
threshold = 3 * 1.4826 * roll_mad.replace(0, np.nan)
df["OUT_HAMPEL"] = (x - roll_med).abs() > threshold

FLAGS = ["OUT_IQR", "OUT_Z", "OUT_MAD", "OUT_HAMPEL"]
df[FLAGS] = df[FLAGS].fillna(False).astype(bool)

# 몇 개 기준에서 동시에 걸렸는가 = 신뢰도
df["VOTES"] = df[FLAGS].sum(axis=1)
df["OUTLIER_LEVEL"] = np.select(
    [df["VOTES"] >= 3, df["VOTES"] == 2, df["VOTES"] == 1],
    ["확실", "의심", "경미"],
    default="정상",
)

summary = pd.DataFrame(
    {
        "METHOD": FLAGS,
        "DETECTED": [int(df[f].sum()) for f in FLAGS],
    }
)
summary["TOTAL"] = len(df)
summary["DETECT_PCT"] = (summary["DETECTED"] / summary["TOTAL"] * 100).round(3)

df[["Z", "ROBUST_Z"]] = df[["Z", "ROBUST_Z"]].round(3)

output = df
output_summary = summary

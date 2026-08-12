---
title: "07. 그룹 통계를 원본 행에 되붙이기 (transform)"
parent: 예제 모음
nav_order: 7
---

# 07. 그룹 통계를 원본 행에 되붙이기 (transform)
{: .no_toc }

**난이도** ★★☆ · **Level 2 · 재구조화**

설비·공정별 평균/표준편차/중앙값을 계산해 원본 행 수를 유지한 채 Z-score, 순위, 백분위를 한 번에 만듭니다.

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/07_group_stats_transform.py)

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

### 파라미터 요약
{: .no_toc }

| 구분 | 이름 | 타입 | 연결 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement.csv` |
| 출력 | `output` | Table | 새 데이터 테이블 |

---

## 시나리오

"설비마다 공정 조건이 달라서 절대값 비교는 의미가 없다. **자기 그룹 안에서 얼마나 튀는지**로 보고 싶다."

→ 그룹별 평균/표준편차로 표준화(Z-score)하고, 그룹 내 백분위와 순위를 붙입니다.
이때 **행 수는 그대로 유지**되어야 원본 테이블에 그대로 얹을 수 있습니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire에는 `Avg([THICKNESS]) OVER ([EQP_ID])` 같은 **OVER 표현식**이 있어서 평균 정도는 가능합니다. 정직하게 말해 이건 Spotfire도 잘합니다.
- 문제는 **조합**입니다. 로버스트 Z-score(중앙값·MAD 기반), 그룹 내 백분위, 3σ 이탈 플래그, 그룹 표본 수 조건
  (예: 표본 30개 미만 그룹은 판정 제외)을 **한꺼번에** 얹으려면 계산 컬럼이 8~10개로 늘고
  각각을 다시 참조해야 해서 유지보수가 급격히 나빠집니다.
- 데이터 함수는 이 전체를 15줄로 표현하고, **다른 분석에 복사해서 재사용**할 수 있습니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 출력 | `output` | Table | 원본 + 그룹 통계 컬럼 |

## 스크립트

```python
import numpy as np
import pandas as pd

df = input.copy()

GROUP = ["EQP_ID", "STEP_DESC"]
VALUE = "THICKNESS"
MIN_N = 30

g = df.groupby(GROUP)[VALUE]

# transform : 그룹 통계를 '원본 행 수 그대로' 되돌려 준다
df["GRP_N"] = g.transform("size")
df["GRP_MEAN"] = g.transform("mean")
df["GRP_STD"] = g.transform("std")
df["GRP_MEDIAN"] = g.transform("median")

# 표준 Z-score (0으로 나누기 방어)
std_safe = df["GRP_STD"].replace(0, np.nan)
df["Z_SCORE"] = (df[VALUE] - df["GRP_MEAN"]) / std_safe

# 로버스트 Z-score : 중앙값 + MAD 기반이라 이상치에 잘 흔들리지 않는다
mad = g.transform(lambda s: (s - s.median()).abs().median())
mad_safe = mad.replace(0, np.nan)
df["ROBUST_Z"] = 0.6745 * (df[VALUE] - df["GRP_MEDIAN"]) / mad_safe

# 그룹 내 백분위 (0~100)
df["PCTL"] = (g.rank(pct=True) * 100).round(2)

# 판정 : 표본이 적은 그룹은 아예 판정하지 않는다
df["OUTLIER_FLAG"] = np.select(
    [df["GRP_N"] < MIN_N, df["ROBUST_Z"].abs() > 3.5],
    ["INSUFFICIENT", "OUTLIER"],
    default="NORMAL",
)

num_cols = ["GRP_MEAN", "GRP_STD", "GRP_MEDIAN", "Z_SCORE", "ROBUST_Z"]
df[num_cols] = df[num_cols].round(4)

output = df.reset_index(drop=True)
```

## 핵심 포인트

- **`agg` 와 `transform` 의 차이**가 이 예제의 전부입니다.

  | | 결과 행 수 | 용도 |
  |---|---|---|
  | `groupby().agg()` | **그룹 수**만큼 (줄어듦) | 요약 테이블 |
  | `groupby().transform()` | **원본과 동일** | 원본에 되붙이기 |

- 표준편차가 0이면 Z-score가 무한대가 됩니다. `replace(0, np.nan)` 로 방어하세요.
- **MAD(중앙값 절대편차) 기반 로버스트 Z-score**는 이상치에 흔들리지 않습니다.
  `0.6745 × (x - median) / MAD` 가 표준 정의이며, 반도체 계측처럼 스파이크가 섞인 데이터에 적합합니다.
- `rank(pct=True)` 는 그룹 내 백분위(0~1)를 바로 줍니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수.
입력 input, 그룹 키는 EQP_ID + STEP_DESC, 대상 값은 THICKNESS.
원본 행 수를 유지한 채 아래 컬럼을 추가해줘 (groupby().transform() 사용):
- GRP_N, GRP_MEAN, GRP_STD, GRP_MEDIAN
- Z_SCORE (표준 z), ROBUST_Z (중앙값과 MAD 기반, 0.6745 스케일)
- PCTL (그룹 내 백분위 0~100)
- OUTLIER_FLAG : |ROBUST_Z| > 3.5 이면 'OUTLIER', 아니면 'NORMAL'.
  단 GRP_N 이 30 미만인 그룹은 'INSUFFICIENT' 로 표기
표준편차/MAD 가 0인 경우 0으로 나누지 않도록 방어 코드를 넣어줘.
결과는 output.
```

## 확인 & 응용

- `OUTLIER_FLAG` 로 색을 칠한 산점도를 그리면 설비별 이상 웨이퍼가 즉시 보입니다.
- **응용**: 그룹 키를 `LOT_ID` 로 바꾸면 "랏 내 웨이퍼 산포(within-lot uniformity)" 분석이 됩니다.

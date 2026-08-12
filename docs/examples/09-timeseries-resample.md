---
title: "09. 시간 단위 재집계와 "비어 있는 시간" 채우기"
parent: 예제 모음
nav_order: 9
---

# 09. 시간 단위 재집계와 "비어 있는 시간" 채우기
{: .no_toc }

**난이도** ★★☆ · **Level 3 · 시계열과 공정 분석**

불규칙한 이벤트 로그를 시간당/일별 격자로 재집계하고, 데이터가 아예 없는 구간을 0 또는 결측으로 명시적으로 만들어 냅니다.

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/09_timeseries_resample.py)

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
| 입력 | `freq` | Value | 문서 속성 (예: `1h`) |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_gap` | Table | 새 데이터 테이블 |

---

## 시나리오

계측 로그는 **불규칙한 시각**에 찍힙니다. 이것을 "설비별 1시간 단위 처리량/평균 두께" 격자로 바꿔야
설비 간 비교, 교대조 비교, 이상 구간 탐지가 가능해집니다.

여기서 진짜 중요한 건 **"데이터가 없는 시간"** 입니다.
설비가 멈춰 있던 3시간은 원본 데이터에 **행 자체가 없기 때문에**, 그냥 집계하면 그 시간이 사라져
차트에서 선이 그냥 이어져 버립니다. 다운타임이 눈에 보이지 않게 됩니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- 시간 단위 집계 자체는 계산 컬럼(`DateTimeCeiling` 등) + 집계로 가능합니다.
- 그러나 **없는 시간을 만들어 내는 것은 불가능**합니다. 존재하지 않는 행을 시각화가 만들어 낼 수는 없으니까요.
  달력 테이블을 따로 만들어 outer join 하는 우회법이 있지만, 매번 수작업입니다.
- 데이터 함수의 `resample()` 은 **빈 구간을 자동으로 생성**합니다. 이게 핵심 차이입니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 입력 | `freq` | Value (String) | 문서 속성 `Freq` — `15min` / `1h` / `1D` |
| 출력 | `output` | Table | 시간 격자 집계 결과 |
| 출력 | `output_gap` | Table | 데이터가 없던 구간(다운타임 후보) 목록 |

> `freq` 를 문서 속성 드롭다운(`15min;1h;1D`)에 연결하면 사용자가 화면에서 집계 단위를 바꿀 수 있습니다.

## 스크립트

```python
import numpy as np
import pandas as pd

df = input.copy()
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])

# 모든 설비가 공통으로 가질 시간 격자 범위
t_min = df["MEAS_TIME"].min().floor(freq)
t_max = df["MEAS_TIME"].max().ceil(freq)
grid = pd.date_range(t_min, t_max, freq=freq)

frames = []
for eqp, block in df.groupby("EQP_ID", sort=True):
    agg = (
        block.set_index("MEAS_TIME")
        .resample(freq)
        .agg(
            N_MEAS=("THICKNESS", "size"),
            THICKNESS_MEAN=("THICKNESS", "mean"),
            THICKNESS_STD=("THICKNESS", "std"),
            PARTICLE_SUM=("PARTICLE_CNT", "sum"),
        )
    )
    # 공통 격자에 맞춰 없는 구간까지 행으로 만들어 준다
    agg = agg.reindex(grid)
    agg["N_MEAS"] = agg["N_MEAS"].fillna(0).astype(int)
    agg["PARTICLE_SUM"] = agg["PARTICLE_SUM"].where(agg["N_MEAS"] > 0)
    agg.insert(0, "EQP_ID", eqp)
    agg.index.name = "TIME_BIN"
    frames.append(agg.reset_index())

res = pd.concat(frames, ignore_index=True)
res["HAS_DATA"] = res["N_MEAS"] > 0

# 연속으로 비어 있는 구간을 하나의 '갭'으로 묶는다
res = res.sort_values(["EQP_ID", "TIME_BIN"]).reset_index(drop=True)
new_block = (res["HAS_DATA"] != res.groupby("EQP_ID")["HAS_DATA"].shift()) | (
    res["EQP_ID"] != res["EQP_ID"].shift()
)
res["BLOCK_ID"] = new_block.cumsum()

gaps = (
    res[~res["HAS_DATA"]]
    .groupby(["EQP_ID", "BLOCK_ID"], as_index=False)
    .agg(GAP_START=("TIME_BIN", "min"), GAP_END=("TIME_BIN", "max"), BINS=("TIME_BIN", "size"))
)
bin_hours = pd.Timedelta(freq) / pd.Timedelta("1h")
gaps["GAP_HOURS"] = (gaps["BINS"] * bin_hours).round(2)
gaps = gaps.drop(columns=["BLOCK_ID"])

if gaps.empty:  # 빈 출력 방지
    gaps = pd.DataFrame(
        [{"EQP_ID": "NO_GAP", "GAP_START": t_min, "GAP_END": t_min, "BINS": 0, "GAP_HOURS": 0.0}]
    )

num = ["THICKNESS_MEAN", "THICKNESS_STD"]
res[num] = res[num].round(3)

output = res.drop(columns=["BLOCK_ID"])
output_gap = gaps
```

## 핵심 포인트

- `resample()` 은 **DatetimeIndex 가 있어야** 동작합니다. `set_index("MEAS_TIME")` 이 선행 조건입니다.
- 빈도 문자열: `15min`, `1h`, `1D`, `1W`, `1MS`(월초).
  최신 pandas는 소문자 `h`/`min` 을 씁니다. (예전 코드의 `H`, `T` 는 경고가 나거나 동작하지 않습니다.)
- **`count` 가 0인 구간이 곧 다운타임 후보**입니다. 평균값은 `NaN` 으로 두어야 차트에서 선이 끊깁니다.
  0으로 채우면 "두께가 0인 웨이퍼"라는 없는 사실을 만들어 냅니다. **개수는 0, 측정값은 NaN** 이 정답입니다.
- 여러 그룹(설비)이 있을 때는 `groupby` 후 그룹별로 `resample` 하고 다시 합칩니다.
  이때 각 그룹의 시간 범위를 **전체 공통 범위로 맞춰야** 설비 간 비교가 가능합니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input(DataFrame), freq(문자열, 예 '1h').
MEAS_TIME(문자열 시각), EQP_ID, THICKNESS, PARTICLE_CNT 컬럼이 있어.
1. EQP_ID 별로 freq 단위 시간 격자를 만들고 아래를 집계
   - N_MEAS: 계측 건수, THICKNESS_MEAN/STD, PARTICLE_SUM
2. 모든 설비가 '전체 데이터의 최소~최대 시각' 범위를 공통으로 갖도록 빈 구간도 행으로 생성
3. 계측이 0건인 구간은 N_MEAS=0, 측정값 컬럼은 NaN 으로 둘 것 (0으로 채우지 말 것)
4. 연속으로 비어 있는 구간을 묶어 (EQP_ID, GAP_START, GAP_END, GAP_HOURS) 형태로 별도 출력
출력: output, output_gap. 전부 결측인 컬럼이 생기지 않도록 주의.
```

## 확인 & 응용

- `output` 으로 라인 차트를 그리고 `N_MEAS = 0` 구간에 색을 칠하면 다운타임이 한눈에 보입니다.
- **응용**: `sales_orders.csv` 로 주 단위 수주 금액 추이를 만들고, 수주가 없던 주를 표시해 보세요.

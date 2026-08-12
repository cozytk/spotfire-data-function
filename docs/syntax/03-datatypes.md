---
title: 3. 데이터 타입과 결측치
parent: 문법
nav_order: 3
---

# 3. 데이터 타입과 결측치
{: .no_toc }

데이터 함수 오류의 상당수가 **타입** 문제입니다.
이 장의 표 두 개만 기억해도 대부분의 사고를 예방할 수 있습니다.
{: .fs-5 .fw-300 }

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## Spotfire ↔ pandas 타입 매핑

Spotfire 데이터 테이블이 Python으로 넘어올 때의 대응 관계입니다.

| Spotfire 타입 | pandas dtype | 비고 |
|---|---|---|
| Integer | `int32` / `Int32` | 결측이 있으면 실수형이나 nullable 정수형이 됨 |
| LongInteger | `int64` / `Int64` | |
| Real | `float64` | |
| SingleReal | `float32` | |
| Currency | `object` (Decimal) | 계산 전 `astype(float)` 권장 |
| String | `object` (`str`) | |
| Boolean | `bool` | |
| Date | `datetime64[ns]` | 시각 부분은 00:00:00 |
| DateTime | `datetime64[ns]` | |
| Time | `object` (`time`) | 날짜 없이 시각만 |
| TimeSpan | `timedelta64[ns]` | |
| Binary | `bytes` | 이미지 등 |

- **Column** 입력 → `pandas.Series`
- **Table** 입력 → `pandas.DataFrame`

{: .주의 }
> **정수 컬럼에 결측이 하나라도 있으면 `float64` 로 바뀝니다.**
> `WAFER_NO` 가 `1, 2, 3` 이 아니라 `1.0, 2.0, 3.0` 으로 보이는 이유입니다.
> 결과를 다시 정수로 내보내려면 결측을 채운 뒤 `astype(int)` 하거나,
> 결측을 유지해야 한다면 `astype("Int64")`(대문자 I) 를 쓰세요.

## 날짜·시간 다루기

CSV나 데이터베이스에서 온 시각은 **문자열인 경우가 많습니다.**
계산 전에 반드시 변환하세요.

```python
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])                 # 표준 형식 자동 인식
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"], errors="coerce")  # 실패 시 NaT (안전)
df["MEAS_TIME"] = pd.to_datetime(df["DATE_STR"], format="%Y%m%d")   # 형식 명시 (가장 빠르고 정확)
```

변환 후 쓸 수 있는 것들:

```python
df["MEAS_TIME"].dt.date          # 날짜만
df["MEAS_TIME"].dt.hour          # 시
df["MEAS_TIME"].dt.dayofweek     # 요일 (월=0)
df["MEAS_TIME"].dt.to_period("M")  # 월 단위
(df["END"] - df["START"]).dt.total_seconds() / 60   # 분 단위 소요시간
```

### 교대조(Shift) 계산 예시

현업에서 자주 나오는 요구입니다.

```python
import numpy as np

hour = df["MEAS_TIME"].dt.hour
df["SHIFT"] = np.select(
    [(hour >= 6) & (hour < 14), (hour >= 14) & (hour < 22)],
    ["주간(A)", "오후(B)"],
    default="야간(C)",
)
```

## 결측치의 여러 얼굴

pandas에서 "비어 있음"은 한 종류가 아닙니다.

| 표기 | 의미 | 주로 나타나는 곳 |
|---|---|---|
| `np.nan` | 숫자형 결측 | 숫자 컬럼 |
| `None` | 파이썬 None | 문자열/객체 컬럼 |
| `pd.NaT` | 날짜/시간 결측 | datetime 컬럼 |
| `pd.NA` | nullable 타입 결측 | `Int64`, `string` 등 |

**전부 `isna()` 로 한 번에 잡을 수 있습니다.**

```python
df.isna().sum()               # 컬럼별 결측 개수 — 데이터를 받으면 가장 먼저 하는 일
df["X"].isna()                # 결측 여부 (True/False)
df["X"].notna()               # 결측이 아닌지
```

{: .주의 }
> **`df["X"] == np.nan` 은 항상 False 입니다.** `NaN` 은 자기 자신과도 같지 않기 때문입니다.
> 반드시 `isna()` / `notna()` 를 쓰세요.

### 빈 문자열은 결측이 아니다

Spotfire에서 넘어온 문자열 컬럼의 `""` 는 `NaN` 이 **아닙니다.** `dropna()` 로 지워지지 않습니다.

```python
import numpy as np
df = df.replace(r"^\s*$", np.nan, regex=True)   # 공백만 있는 문자열도 결측으로 통일
```

### 0은 결측인가?

**데이터를 받으면 반드시 물어야 할 질문입니다.**

| 컬럼 | 0의 의미 |
|---|---|
| `PARTICLE_CNT` (파티클 수) | 진짜 0 — **정상값** |
| `PRESSURE` (압력) | 센서 미취득 — **결측** |
| `Glucose` (혈당, diabetes 데이터) | 측정 안 함 — **결측** |

0을 결측으로 처리하지 않으면 평균이 실제보다 낮게 나옵니다.
반대로 정상값 0을 지우면 멀쩡한 데이터가 사라집니다.

```python
ZERO_IS_MISSING = ["PRESSURE", "TEMP"]        # 컬럼을 명시적으로 지정할 것
df[ZERO_IS_MISSING] = df[ZERO_IS_MISSING].replace(0, np.nan)
```

{: .주의 }
> **`df[(df != 0).all(axis=1)]` 처럼 전체 컬럼을 일괄 검사하지 마세요.**
> 0이 정상값인 컬럼(카운트, 플래그, 순번)까지 행을 지워 버립니다.
> 자세한 내용은 [02번 예제](../../examples/02-missing-and-zero/).

## 결측 처리 방법 선택

| 방법 | 코드 | 언제 |
|---|---|---|
| 삭제 | `df.dropna(subset=["X"])` | 결측이 적고, 그 행이 분석에 필수일 때 |
| 상수 대치 | `df.fillna({"X": 0})` | 0/미분류가 의미를 갖는 경우 |
| 그룹 통계 대치 | `df.groupby("G")["X"].transform("median")` | **가장 권장** — 조건별 특성 반영 |
| 앞/뒤 값 | `df["X"].ffill()` / `bfill()` | 범주형, 상태값 |
| 보간 | `df["X"].interpolate(method="time")` | 시간에 따라 연속적인 값 |

실습: [08번 예제 — 결측치 똑똑하게 채우기](../../examples/08-impute-smart/)

## 출력할 때의 타입 규칙

Spotfire로 결과를 되돌려 줄 때 **반드시 지켜야 하는 것들**입니다.

| 규칙 | 이유 |
|---|---|
| 컬럼명은 **문자열**이어야 한다 | 피벗 결과의 숫자 컬럼명이 대표적인 사고 지점 |
| **전부 결측인 컬럼**을 만들지 않는다 | Spotfire가 타입을 결정할 수 없어 오류 |
| 셀 안에 **list/dict를 넣지 않는다** | 내보낼 수 없는 타입 |
| MultiIndex는 **평탄화**한다 | `reset_index()` + 컬럼명 문자열화 |
| 범주형(`category`)은 문자열로 변환 | `astype(str)` |

```python
# 피벗 후 필수 정리 3종 세트
pv = pv.reset_index()
pv.columns = [str(c) for c in pv.columns]
pv.columns.name = None
```

---

## 정리

- 정수 컬럼에 결측이 있으면 실수형이 된다
- 시각은 항상 `pd.to_datetime()` 으로 변환하고 시작
- 결측은 `isna()` 로 확인 — `== np.nan` 은 동작하지 않음
- **"이 컬럼의 0은 진짜 0인가?"** 를 항상 확인
- 출력 전에 **컬럼명 문자열화 / 인덱스 해제 / 전부 결측 컬럼 제거**

다음: [출력 규칙과 자주 나는 오류](../04-output-errors/)

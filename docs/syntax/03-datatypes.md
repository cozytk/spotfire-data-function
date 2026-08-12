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
아래 표는 공식 `spotfire` 패키지로 **실제 왕복시켜 측정한 결과**입니다.

| Spotfire 타입 | 데이터 함수 안의 dtype | 셀 값의 파이썬 타입 | `.dt`/`.str` |
|---|---|---|---|
| Boolean | **`object`** | `bool` | — |
| Integer | `Int32` (nullable) | `numpy.int32` | — |
| LongInteger | `Int64` (nullable) | `numpy.int64` | — |
| SingleReal | `float32` | `numpy.float32` | — |
| Real | `float64` | `numpy.float64` | — |
| DateTime | **`object`** | `datetime.datetime` | ❌ 변환 필요 |
| Date | **`object`** | `datetime.date` | ❌ 변환 필요 |
| Time | **`object`** | `datetime.time` | ❌ 변환 필요 |
| TimeSpan | **`object`** | `datetime.timedelta` | ❌ 변환 필요 |
| String | `object` | `str` | ✅ `.str` 사용 가능 |
| Binary | `object` | `bytes` | — |
| Currency | `object` | `decimal.Decimal` | 계산 전 `astype(float)` |

- **Column** 입력 → `pandas.Series`
- **Table** 입력 → `pandas.DataFrame`
- **Value** 입력 → `str` / `int` / `float` / `bool` / `datetime` (연결한 값의 타입)

{: .주의 }
> ## 가장 많이 걸려 넘어지는 함정: 시각 컬럼은 `datetime64` 가 아닙니다
>
> Spotfire의 DateTime 컬럼은 **`object` dtype 에 `datetime.datetime` 객체가 담긴 형태**로 들어옵니다.
> pandas의 `datetime64[ns]` 가 **아닙니다.** 그래서 이렇게 하면 실패합니다.
>
> ```python
> df["MEAS_TIME"].dt.hour
> # AttributeError: Can only use .dt accessor with datetimelike values
> ```
>
> **데이터 함수 맨 앞에서 변환하고 시작하세요.** 이 한 줄이 오류의 상당수를 없앱니다.
>
> ```python
> df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])   # 이후 .dt 사용 가능
> ```
>
> 로컬에서 CSV로 개발할 때는 시각이 **문자열**이라 `pd.to_datetime()` 이 어차피 필요합니다.
> 그래서 이 습관을 들이면 로컬과 Spotfire **양쪽에서 모두** 동작합니다.

### 입력 직후에 붙이는 정규화 블록

타입 때문에 생기는 문제를 한 번에 없애는 관용구입니다. 필요한 줄만 남겨 쓰세요.

```python
import pandas as pd

df = input.copy()

df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])     # DateTime/Date  → datetime64[ns]
df["DURATION"]  = pd.to_timedelta(df["DURATION"])     # TimeSpan       → timedelta64[ns]
df["IS_OK"]     = df["IS_OK"].astype("boolean")       # Boolean(object) → nullable bool
df["AMOUNT"]    = df["AMOUNT"].astype(float)          # Currency        → float
df["WAFER_NO"]  = df["WAFER_NO"].astype("Int64")      # 정수 유지 (결측 허용)
```

{: .팁 }
> 어떤 컬럼이 무슨 타입으로 들어오는지 모르겠다면 **한 줄로 확인**할 수 있습니다.
> ([print 결과를 보는 법](../06-run-debug/))
>
> ```python
> print(input.dtypes.to_string())
> print(input.iloc[0].map(type).to_string())   # 셀 값의 실제 파이썬 타입
> ```

### 정수 컬럼은 nullable 타입으로 들어온다

Spotfire의 Integer/LongInteger는 `Int32`/`Int64`(**대문자 I**)로 들어옵니다.
numpy의 `int64` 가 아니라 **결측을 담을 수 있는 pandas 확장 타입**입니다.

| | numpy `int64` | pandas `Int64` |
|---|---|---|
| 결측 표현 | 불가능 | `pd.NA` |
| 결측 있는 연산 | — | 결과도 `pd.NA` (`NaN` 아님) |
| `np.isnan()` | 동작 | **동작 안 함** — `pd.isna()` 를 쓸 것 |
| scikit-learn 등에 투입 | 가능 | **거부되는 경우 있음** → `astype(float)` |

```python
# 외부 라이브러리에 넘기기 전에는 일반 float 로 바꾸는 편이 안전합니다
X = df[["THICKNESS", "PARTICLE_CNT"]].astype(float).to_numpy()
```

{: .주의 }
> **정수 컬럼에 결측이 섞이면 Spotfire 쪽에서 이미 Real(실수)로 넘어옵니다.**
> `WAFER_NO` 가 `1, 2, 3` 이 아니라 `1.0, 2.0, 3.0` 으로 보이는 이유입니다.
> 결과를 다시 정수로 내보내려면 결측을 채운 뒤 `astype(int)`,
> 결측을 유지해야 한다면 `astype("Int64")` 를 쓰세요.

## 날짜·시간 다루기

앞에서 본 대로 **변환이 먼저**입니다.

```python
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])                   # Spotfire DateTime / 표준 문자열
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
그리고 **Spotfire가 어떤 타입의 컬럼을 주느냐에 따라 결측의 모양이 달라집니다.**

| Spotfire 타입 | 데이터 함수 안의 결측값 | 표기 |
|---|---|---|
| Integer / LongInteger | `pd.NA` | `<NA>` |
| Real / SingleReal | `np.nan` | `NaN` |
| String / Boolean / DateTime / Date / Time / TimeSpan / Binary / Currency | `None` | `None` |

{: .주의 }
> **시각 컬럼의 결측은 `pd.NaT` 가 아니라 `None` 입니다.**
> `pd.to_datetime()` 으로 변환하고 나면 그때 `NaT` 가 됩니다.
> 어느 쪽이든 `isna()` 로는 똑같이 잡히므로, **결측 판정은 항상 `isna()`** 로 하세요.

세 가지 표기의 일반적인 의미는 이렇습니다.

| 표기 | 의미 | 주로 나타나는 곳 |
|---|---|---|
| `np.nan` | 숫자형 결측 | 실수 컬럼 |
| `None` | 파이썬 None | 문자열/객체 컬럼 |
| `pd.NaT` | 날짜/시간 결측 | `datetime64` 로 변환한 뒤 |
| `pd.NA` | nullable 타입 결측 | `Int64`, `boolean`, `string` |

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

## 내보낼 때: pandas dtype → Spotfire 타입

출력은 **dtype 을 보고 자동으로 결정**됩니다. 실측 결과는 이렇습니다.

| 내보낸 dtype | Spotfire 타입 | 주의 |
|---|---|---|
| `bool` | Boolean | |
| `int32` / `Int32` | Integer | |
| `int64` / `Int64` | **LongInteger** | `int` 는 기본이 int64 → LongInteger |
| `float32` | SingleReal | |
| `float64` | Real | |
| `datetime64[ns]` | DateTime | |
| `timedelta64[ns]` | TimeSpan | |
| `object` (`datetime.date`) | Date | |
| `object` (`datetime.time`) | Time | |
| `object` (`str`) | String | |
| `object` (`Decimal`) | Currency | |
| `object` (`bytes`) | Binary | 이미지 등 |
| `category` | String | |

{: .팁 }
> **날짜만 필요한데 DateTime 으로 나가는 게 싫다면** `.dt.date` 로 `datetime.date` 를 만드세요.
> ```python
> df["MEAS_DATE"] = pd.to_datetime(df["MEAS_TIME"]).dt.date   # → Spotfire Date
> ```

## Spotfire가 거부하는 출력

아래는 실제로 발생하는 오류 메시지와 함께 정리한 것입니다.
**출력을 만들고 나면 이 5가지를 확인**하세요.

| 만들면 안 되는 것 | 실제 오류 메시지 |
|---|---|
| **전부 결측인 컬럼** | `cannot determine type for column 'X'; all values are missing` |
| 셀 안의 **list / dict** | `unknown type 'list' in column 'X'` |
| 한 컬럼에 **섞인 타입** | `types in column 'X' do not match` |
| **중복된 컬럼명** | `obj does not have unique column names` |
| **컬럼이 하나도 없는** DataFrame | `No objects to concatenate` |

- 컬럼명이 **문자열이 아니면** 안 됩니다. 피벗 결과의 숫자·날짜 컬럼명이 대표적인 사고 지점입니다.
- **0행은 괜찮습니다.** 단, 컬럼의 dtype 이 정해져 있어야 합니다
  (`Int64` 인 빈 컬럼은 통과, `object` 인 빈 컬럼은 위의 "전부 결측" 오류).

```python
# 피벗 후 필수 정리 3종 세트
pv = pv.reset_index()
pv.columns = [str(c) for c in pv.columns]
pv.columns.name = None
```

{: .주의 }
> ## 인덱스는 Spotfire로 전달되지 않습니다
>
> `groupby()` 결과를 그대로 내보내면 **그룹 키가 소리 없이 사라집니다.**
> 오류도 나지 않아서 더 위험합니다.
>
> ```python
> output = df.groupby("EQP_ID")["THICKNESS"].mean()
> # Spotfire 에 도착하는 것: THICKNESS 한 컬럼뿐. EQP_ID 가 없다!
> ```
>
> 둘 중 하나를 반드시 하세요.
>
> ```python
> output = df.groupby("EQP_ID", as_index=False)["THICKNESS"].mean()   # 권장
> output = df.groupby("EQP_ID")["THICKNESS"].mean().reset_index()     # 동일한 결과
> ```

### 전부 결측인 컬럼을 꼭 내보내야 한다면

`spotfire` 헬퍼로 **타입을 직접 지정**하면 통과합니다.
자세한 내용은 [7. spotfire 헬퍼 모듈](../07-spotfire-module/)에 있습니다.

```python
import spotfire

result["REMARK"] = None                                  # 아직 값이 없는 컬럼
spotfire.set_spotfire_types(result, {"REMARK": "String"})  # 타입을 못 박아 준다
output = result
```

---

## 정리

- **시각 컬럼은 `object` 로 들어온다** — `pd.to_datetime()` 으로 변환하고 시작
- 정수는 nullable `Int32`/`Int64`, 결측이 섞이면 아예 실수로 들어온다
- 결측 모양은 타입마다 다르다 (`pd.NA` / `NaN` / `None`) — 판정은 항상 `isna()`
- **"이 컬럼의 0은 진짜 0인가?"** 를 항상 확인
- 출력 전에 **컬럼명 문자열화 / `reset_index()` / 전부 결측 컬럼 처리**

다음: [출력 규칙과 자주 나는 오류](../04-output-errors/)

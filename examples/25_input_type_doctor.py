'''---
title: 입력 타입 진단기 — "왜 내 코드가 Spotfire에서만 터지나"
level: 1
difficulty: ★☆☆
summary: Spotfire가 실제로 넘겨준 컬럼 타입을 표로 뽑아 보고, .dt 오류를 일으키는 시각 컬럼 등을 자동으로 정규화합니다. 새 데이터 함수를 만들 때 맨 처음 붙여 보는 도구입니다.
data: [fab_measurement.csv]
inputs:
  input:
    file: fab_measurement.csv
outputs: [output, output_schema]
---
## 시나리오

로컬 Jupyter에서는 잘 돌던 코드를 Spotfire에 붙여 넣었더니 이런 오류가 납니다.

```text
AttributeError: Can only use .dt accessor with datetimelike values
```

컬럼 이름도 맞고, 데이터도 그대로인데 왜 터질까요?
**Spotfire가 넘겨주는 dtype이 CSV에서 읽은 dtype과 다르기 때문**입니다.

| | 로컬에서 `pd.read_csv()` | Spotfire 데이터 함수 |
|---|---|---|
| `MEAS_TIME` | `object` (문자열) | `object` (**`datetime.datetime` 객체**) |
| `WAFER_NO` | `int64` | **`Int64`** (nullable) |
| `IS_OK` | `object` / `bool` | `object` (**`bool` 객체**) |

이름은 같은 `object` 인데 **안에 든 것이 다릅니다.**
그래서 `df["MEAS_TIME"].str.slice(0, 10)` 도, `df["MEAS_TIME"].dt.hour` 도 실패합니다.

이 예제는 **"지금 내 손에 들어온 데이터가 정확히 무엇인지"를 표로 보여 주는 진단기**입니다.
새 데이터 함수를 만들 때 **맨 처음 한 번 돌려 보는 용도**로 만들었습니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire 데이터 테이블 속성 창에서도 컬럼 타입은 볼 수 있습니다.
  하지만 그것은 **Spotfire 쪽 타입**이고, 우리가 알아야 하는 것은
  **파이썬으로 건너온 뒤의 모습**입니다. 둘은 1:1이 아닙니다.
- 결측 개수, 고유값 수, 실제 셀 값의 파이썬 타입을 **한 표에 모아** 보는 화면은 없습니다.
- 무엇보다, 이 예제의 후반부처럼 **자동으로 정규화까지** 해 주지는 않습니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | 진단하고 싶은 아무 테이블 |
| 출력 | `output` | Table | 타입이 정규화된 테이블 (이후 작업의 시작점) |
| 출력 | `output_schema` | Table | 컬럼별 진단 결과 |

> 입력을 **어떤 테이블에 연결해도** 동작합니다. 컬럼 이름을 하나도 가정하지 않기 때문입니다.
> 라이브러리에 저장해 두고 필요할 때마다 꺼내 쓰세요.

## 스크립트

{{CODE}}

## 핵심 포인트

- **`dtype` 만 봐서는 부족합니다.** Spotfire의 String·Boolean·DateTime·TimeSpan·Binary·Currency가
  전부 `object` 이기 때문입니다. **셀 값의 파이썬 타입**을 함께 봐야 정체를 알 수 있습니다.
  그래서 진단표에 `VALUE_TYPE` 컬럼을 넣었습니다.
- 정규화는 **원본을 덮어쓰지 않고 규칙이 명확한 것만** 합니다.
  `datetime` → `datetime64[ns]`, `timedelta` → `timedelta64[ns]`,
  `Decimal` → `float`, `bool` → `boolean`. 문자열은 건드리지 않습니다.
- `ACTION` 컬럼에 **무엇을 바꿨는지** 남깁니다. 자동 변환은 편하지만
  "언제 무엇이 바뀌었는지 모르는" 상태가 되면 더 위험합니다.
- 진단표의 `NULL_PCT` 가 100%인 컬럼은 그대로 내보내면
  `cannot determine type for column ...` 오류가 납니다. 그래서 마지막에 경고를 남깁니다.

{: .팁 }
> 입력 테이블이 SBDF에서 곧바로 온 경우에는 `spotfire.get_spotfire_types(input)` 으로
> **Spotfire 쪽 원래 타입**을 직접 물어볼 수도 있습니다.
> 이 예제는 그 정보가 없을 때도 동작하도록 dtype과 셀 값에서 추정합니다.
> ([7. `spotfire` 모듈](../../syntax/07-spotfire-module/))

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수를 만들어 줘. 입력은 input(DataFrame) 하나.
컬럼 이름을 전혀 가정하지 말고 아래를 해 줘.

1. 컬럼별로 다음을 담은 진단 테이블 output_schema 를 만들 것
   - COLUMN, PANDAS_DTYPE, VALUE_TYPE(셀 값의 실제 파이썬 타입 이름),
     SPOTFIRE_TYPE(추정), NULL_CNT, NULL_PCT, NUNIQUE, SAMPLE(문자열), ACTION
2. output 은 input 을 아래 규칙으로 정규화한 것
   - 셀 값이 datetime.datetime/date 인 object 컬럼 -> pd.to_datetime
   - 셀 값이 datetime.timedelta 인 object 컬럼 -> pd.to_timedelta
   - 셀 값이 decimal.Decimal 인 컬럼 -> float
   - 셀 값이 bool 인 object 컬럼 -> "boolean" dtype
   - 문자열 컬럼은 건드리지 말 것
3. 무엇을 바꿨는지 ACTION 컬럼에 기록할 것
4. 전부 결측인 컬럼은 ACTION 에 경고를 남길 것
5. inplace 쓰지 말고, 출력에 전부 결측인 컬럼이 생기지 않게 할 것
```

## 확인 & 응용

- `output_schema` 를 표로 띄워 두면 **데이터가 바뀌었을 때 바로 눈에 띕니다.**
  "어제까지 Real이던 컬럼이 오늘 String으로 들어옴" 같은 사고를 조기에 잡습니다.
- **응용 1**: `NULL_PCT` 가 임계값을 넘는 컬럼만 걸러 "데이터 품질 경고" 테이블로 만들어 보세요.
- **응용 2**: `output` 을 다른 데이터 함수의 입력으로 연결하면,
  타입 정규화가 끝난 상태에서 본 작업을 시작할 수 있습니다.
- **응용 3**: `NUNIQUE == 1` 인 컬럼(값이 하나뿐)과 `NUNIQUE == len(df)` 인 컬럼(사실상 키)을
  표시하면 분석 대상 컬럼을 고를 때 도움이 됩니다.
'''
import datetime as dt
from decimal import Decimal

import pandas as pd

df = input.copy()

# ---------------------------------------------------------------- 1) 진단
# dtype 과 '셀 값의 실제 파이썬 타입' 을 함께 봐야 Spotfire 타입을 알 수 있다.
# Spotfire 의 String/Boolean/DateTime/Date/Time/TimeSpan/Binary/Currency 는 모두 object 이다.
VALUE_TYPE_TO_SPOTFIRE = {
    "bool": "Boolean",
    "datetime": "DateTime",
    "date": "Date",
    "time": "Time",
    "timedelta": "TimeSpan",
    "Decimal": "Currency",
    "bytes": "Binary",
    "str": "String",
}
DTYPE_TO_SPOTFIRE = {
    "int32": "Integer", "Int32": "Integer",
    "int64": "LongInteger", "Int64": "LongInteger",
    "float32": "SingleReal", "float64": "Real",
    "bool": "Boolean", "boolean": "Boolean",
    "datetime64[ns]": "DateTime", "timedelta64[ns]": "TimeSpan",
    "category": "String",
}


def first_valid(s: pd.Series):
    """결측이 아닌 첫 값. 전부 결측이면 None."""
    idx = s.first_valid_index()
    return None if idx is None else s.loc[idx]


def value_type_name(s: pd.Series) -> str:
    v = first_valid(s)
    return "-" if v is None else type(v).__name__


def guess_spotfire_type(s: pd.Series) -> str:
    """이 컬럼이 Spotfire 쪽에서 어떤 타입이었는지 추정한다."""
    dtype = str(s.dtype)
    if dtype != "object":
        return DTYPE_TO_SPOTFIRE.get(dtype, "String")
    return VALUE_TYPE_TO_SPOTFIRE.get(value_type_name(s), "String")


rows = []
n = len(df)
for col in df.columns:
    s = df[col]
    null_cnt = int(s.isna().sum())
    sample = first_valid(s)
    rows.append({
        "COLUMN": str(col),
        "PANDAS_DTYPE": str(s.dtype),
        "VALUE_TYPE": value_type_name(s),
        "SPOTFIRE_TYPE": guess_spotfire_type(s),
        "NULL_CNT": null_cnt,
        "NULL_PCT": round(null_cnt / n * 100, 2) if n else 0.0,
        "NUNIQUE": int(s.nunique(dropna=True)),
        "SAMPLE": "(전부 결측)" if sample is None else str(sample)[:60],
        "ACTION": "",
    })

schema = pd.DataFrame(rows)

# ---------------------------------------------------------------- 2) 정규화
# 규칙이 분명한 것만 바꾼다. 문자열 컬럼은 손대지 않는다.
action = {}

for col in df.columns:
    s = df[col]
    if str(s.dtype) != "object":
        continue
    kind = value_type_name(s)

    if kind in ("datetime", "date"):
        df[col] = pd.to_datetime(s, errors="coerce")
        action[col] = f"{kind} → datetime64[ns] (.dt 사용 가능)"
    elif kind == "timedelta":
        df[col] = pd.to_timedelta(s, errors="coerce")
        action[col] = "timedelta → timedelta64[ns] (.dt 사용 가능)"
    elif kind == "Decimal":
        df[col] = s.map(lambda v: float(v) if isinstance(v, Decimal) else v).astype("float64")
        action[col] = "Currency(Decimal) → float64 (산술 연산 가능)"
    elif kind == "bool":
        df[col] = s.astype("boolean")
        action[col] = "bool(object) → boolean (결측 허용 불리언)"

# 전부 결측인 컬럼은 이대로 내보내면 Spotfire 가 거부한다
all_null = [c for c in df.columns if df[c].isna().all()]
for col in all_null:
    action[col] = "⚠ 전부 결측 — 내보내려면 spotfire.set_spotfire_types() 로 타입 지정 필요"

schema["ACTION"] = schema["COLUMN"].map(action).fillna("변경 없음")

# ---------------------------------------------------------------- 3) 출력
# 진단 결과를 눈에 띄는 순서로: 바꾼 것과 경고를 위로
schema["_ORDER"] = schema["ACTION"].map(
    lambda a: 0 if a.startswith("⚠") else (1 if a != "변경 없음" else 2)
)
output_schema = schema.sort_values(["_ORDER", "COLUMN"]).drop(columns="_ORDER").reset_index(drop=True)

output = df.reset_index(drop=True)

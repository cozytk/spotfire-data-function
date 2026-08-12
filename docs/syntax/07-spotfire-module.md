---
title: 7. spotfire 모듈 — 타입 고정과 메타데이터
parent: 문법
nav_order: 7
---

# 7. `spotfire` 모듈 — 타입 고정과 메타데이터
{: .no_toc }

pandas만으로는 해결되지 않는 문제가 두 가지 있습니다.
**"전부 결측인 컬럼을 내보내야 할 때"** 와 **"단위·표시 형식을 함께 넘기고 싶을 때"** 입니다.
Spotfire에 번들된 `spotfire` 모듈이 그 답입니다.
{: .fs-5 .fw-300 }

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## 이 모듈은 이미 설치되어 있습니다

`spotfire` 는 Spotfire가 데이터 함수를 실행할 때 **실제로 사용하는 바로 그 패키지**입니다.
여러분의 스크립트를 읽어 실행하고 결과를 SBDF로 써 주는 주체가 이 패키지입니다.
따라서 데이터 함수 안에서는 **추가 설치 없이 그냥 import** 하면 됩니다.

```python
import spotfire
```

{: .참고 }
> 로컬 PC에서 개발·검증할 때는 `pip install spotfire` 로 설치할 수 있습니다
> (PyPI의 [`spotfire`](https://pypi.org/project/spotfire/) 패키지, 공식 배포).
> 이 저장소의 [`scripts/spotfire_sim.py`](https://github.com/cozytk/spotfire-data-function/blob/main/scripts/spotfire_sim.py)
> 가 이 패키지를 이용해 **Spotfire 입출력 규약을 그대로 재현**합니다.

---

## 1. 전부 결측인 컬럼 내보내기 — `set_spotfire_types`

가장 자주 쓰게 되는 기능입니다.

Spotfire는 컬럼의 **값을 보고** 타입을 정합니다. 그런데 값이 전부 비어 있으면
무슨 타입인지 알 방법이 없어서 오류가 납니다.

```text
spotfire.sbdf.SBDFError: cannot determine type for column 'REMARK'; all values are missing
```

`set_spotfire_types()` 로 **타입을 직접 못 박아** 주면 통과합니다.

```python
import pandas as pd
import spotfire

result = input.copy()
result["REMARK"] = None          # 사용자가 나중에 채울 비고 컬럼
result["REVIEWED_AT"] = None     # 아직 검토 전이라 전부 비어 있음

spotfire.set_spotfire_types(result, {
    "REMARK": "String",
    "REVIEWED_AT": "DateTime",
})

output = result
```

### 지정할 수 있는 타입 이름

**대소문자까지 정확히** 아래 12개 중 하나여야 합니다.

| | | | |
|---|---|---|---|
| `Boolean` | `Integer` | `LongInteger` | `SingleReal` |
| `Real` | `DateTime` | `Date` | `Time` |
| `TimeSpan` | `String` | `Binary` | `Currency` |

{: .주의 }
> **틀린 이름을 써도 오류가 나지 않고 경고만 뜹니다.**
> `"Int"`, `"Double"`, `"string"` 같은 이름은 조용히 무시되고,
> 결국 원래의 "타입을 결정할 수 없음" 오류로 되돌아갑니다.
> 위 표의 철자를 그대로 복사해서 쓰세요.
>
> 존재하지 않는 컬럼명을 지정한 경우도 마찬가지로 경고만 뜹니다.

### 정수 타입을 명시적으로 고정하기

pandas의 기본 정수는 `int64` 라서 그냥 내보내면 **LongInteger** 가 됩니다.
Spotfire 쪽 컬럼을 Integer로 맞춰야 한다면 이렇게 고정합니다.

```python
spotfire.set_spotfire_types(result, {"WAFER_NO": "Integer"})
```

### 지금 어떤 타입으로 나가는지 확인하기

```python
import spotfire

print(spotfire.get_spotfire_types(input).to_string())
# LOT_ID          String
# WAFER_NO        Integer
# MEAS_TIME       DateTime
# THICKNESS       Real
```

입력 테이블의 원래 Spotfire 타입을 알 수 있어서, **입력과 같은 타입으로 되돌려 주고 싶을 때**
유용합니다.

---

## 2. 단위·표시 형식 함께 넘기기 — 메타데이터

Spotfire 데이터 테이블과 컬럼에는 **속성(Property)** 을 붙일 수 있습니다.
데이터 함수에서 이 값을 **읽을 수도, 새로 붙여 내보낼 수도** 있습니다.

### 읽기

```python
# 테이블 속성
print(input.spotfire_table_metadata)
# {'Source': ['FAB2'], 'ImportedAt': ['2026-03-02']}

# 컬럼 속성
print(input["THICKNESS"].spotfire_column_metadata)
# {'Unit': ['nm'], 'SpecCenter': [87.5]}
```

{: .주의 }
> 속성이 하나도 없으면 **빈 dict 이 아니라 `AttributeError`** 가 날 수 있습니다.
> 읽을 때는 항상 방어적으로 접근하세요.
>
> ```python
> meta = getattr(input, "spotfire_table_metadata", {}) or {}
> unit = getattr(input["THICKNESS"], "spotfire_column_metadata", {}).get("Unit", ["?"])[0]
> ```

### 쓰기

**값은 리스트로** 넣습니다 (Spotfire 속성은 다중 값을 가질 수 있기 때문입니다).

```python
import spotfire

result = df.groupby("EQP_ID", as_index=False)["THICKNESS"].mean()

result.spotfire_table_metadata = {
    "GeneratedBy": ["설비별 두께 평균 데이터 함수"],
    "SourceRows": [len(df)],
}
result["THICKNESS"].spotfire_column_metadata = {"Unit": ["nm"]}

output = result
```

{: .주의 }
> **컬럼 메타데이터는 `df["컬럼"].속성 = ...` 형태로 바로 대입해야 합니다.**
> 아래처럼 Series를 변수로 꺼내서 설정하면 **반영되지 않습니다.**
>
> ```python
> s = result["THICKNESS"]
> s.spotfire_column_metadata = {"Unit": ["nm"]}   # ❌ 사라짐
> result["THICKNESS"] = s
> ```
>
> 또한 **컬럼을 다시 계산하면 메타데이터가 날아갑니다.**
> 메타데이터 설정은 **모든 가공이 끝난 마지막에** 하세요.

### 입력의 메타데이터를 출력으로 옮기기 — `copy_metadata`

가공을 거치면 메타데이터는 사라집니다. 원본의 속성을 결과에 그대로 물려주려면:

```python
import spotfire

result = input.copy()
result["THICKNESS"] = result["THICKNESS"] * 1000    # nm → pm

spotfire.copy_metadata(input, result)               # 테이블·컬럼 속성 복사
output = result
```

{: .주의 }
> `copy_metadata(source, destination)` 는 **source의 모든 컬럼이 destination에도 있어야** 합니다.
> 없으면 `KeyError` 가 납니다. 집계·선택으로 컬럼이 줄어든 결과에는 쓸 수 없습니다.
> 그런 경우에는 테이블 속성만 직접 옮기세요.
>
> ```python
> result.spotfire_table_metadata = getattr(input, "spotfire_table_metadata", {}) or {}
> ```

---

## 3. 입력·출력 파라미터를 스크립트에서 조회하기

데이터 함수 실행 환경에는 **숨은 전역 변수 두 개**가 준비되어 있습니다.

```python
print([(i.name, i.type) for i in __spotfire_inputs__])
# [('input', 'table'), ('threshold', 'value'), ('marked', 'table')]

print([o.name for o in __spotfire_outputs__])
# ['output', 'output_summary']
```

`type` 은 `'table'` / `'column'` / `'value'` 중 하나이고,
**연결하지 않은 선택 입력은 `'NULL'`** 입니다.

이걸로 **재사용 가능한 방어 코드**를 만들 수 있습니다.

```python
import pandas as pd

# 실제로 연결된 입력만 골라 진단표를 만든다
rows = []
for i in __spotfire_inputs__:
    value = globals().get(i.name)
    rows.append({
        "PARAM": i.name,
        "TYPE": i.type,
        "SHAPE": str(getattr(value, "shape", type(value).__name__)),
        "CONNECTED": "N" if value is None else "Y",
    })
output_debug = pd.DataFrame(rows)
```

{: .팁 }
> 이 패턴은 **"실행은 되는데 결과가 이상하다"** 를 진단할 때 특히 유용합니다.
> 마킹 입력이 0행인지, 선택 파라미터가 연결이 안 된 건지 한눈에 보입니다.

---

## 4. 선택 입력은 `None` 으로 들어온다

입력 파라미터에서 **"필수 파라미터(Required)" 체크를 끄면**,
사용자가 연결하지 않았을 때 그 변수는 **`None`** 이 됩니다. 변수 자체는 존재합니다.

```python
# threshold 를 연결하지 않으면 threshold is None
limit = 3.0 if threshold is None else float(threshold)

df = input[input["THICKNESS"] > limit]
output = df
```

{: .주의 }
> **`NameError` 가 나는 것과 `None` 인 것은 다릅니다.**
> - `NameError` → 파라미터를 **등록하지 않았거나 이름이 틀렸다**
> - `None` → 파라미터는 등록됐지만 **실행 시 연결하지 않았다**
>
> 오류 메시지로 원인을 바로 구분할 수 있습니다.

---

## 정리

| 하고 싶은 일 | 방법 |
|---|---|
| 전부 결측인 컬럼 내보내기 | `spotfire.set_spotfire_types(df, {"컬럼": "String"})` |
| 지금 어떤 타입으로 나가는지 확인 | `spotfire.get_spotfire_types(df)` |
| 단위·출처를 결과에 붙이기 | `df.spotfire_table_metadata` / `df["컬럼"].spotfire_column_metadata` |
| 입력 속성을 결과에 물려주기 | `spotfire.copy_metadata(input, result)` |
| 파라미터 연결 상태 진단 | `__spotfire_inputs__` / `__spotfire_outputs__` |
| 선택 입력 미연결 처리 | `if 파라미터 is None:` |

다음: [AI 활용법 — 원하는 코드 얻어내기](../../prompting/)

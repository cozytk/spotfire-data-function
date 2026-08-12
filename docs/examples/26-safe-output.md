---
title: 26. 출력 안전장치 — Spotfire가 결과를 거부하지 않게 만들기
parent: 예제 모음
nav_order: 26
---

# 26. 출력 안전장치 — Spotfire가 결과를 거부하지 않게 만들기
{: .no_toc }

**난이도** ★★☆ · **Level 4 · 통계·자동화·Spotfire 고유 기능**

계산은 다 끝났는데 마지막 내보내기에서 실패하는 상황을 없앱니다. 인덱스 소실·전부 결측 컬럼·셀 안의 list·혼합 타입을 한 함수로 정리하는 재사용 가능한 안전장치를 만듭니다.

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/26_safe_output.py)

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
| 입력 | `min_count` | Value | 문서 속성 (예: `30`) |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_issue` | Table | 새 데이터 테이블 |

---

## 시나리오

데이터 함수에서 가장 허탈한 실패는 **계산이 다 끝난 뒤에** 나는 오류입니다.

```text
spotfire.sbdf.SBDFError: cannot determine type for column 'REMARK'; all values are missing
```

30초 걸려 집계를 다 해 놓고 마지막 한 줄에서 거부당합니다.
게다가 이 오류들은 **평소에는 안 나다가** 특정 상황에서만 터집니다.

| 언제 터지나 | 무엇이 터지나 |
|---|---|
| 필터를 좁게 걸어 결과가 0행이 됐을 때 | 전부 결측 컬럼 오류 |
| 특정 설비에만 값이 없을 때 | 전부 결측 컬럼 오류 |
| 예외 상황에 문자열을 넣도록 짰을 때 | 혼합 타입 오류 |
| 정규식 결과를 리스트로 담았을 때 | `unknown type 'list'` |
| `groupby()` 결과를 그대로 내보냈을 때 | **오류 없이 그룹 컬럼이 사라짐** |

**시연이 아니라 방어가 목적**인 예제입니다.
여기서 만드는 `finalize()` 를 복사해서 여러분의 데이터 함수 마지막 줄에 붙이면,
위 다섯 가지가 전부 막힙니다.

## 왜 Spotfire 기본 기능으로는 어려운가

Spotfire 기본 기능의 문제가 아니라 **데이터 함수를 쓰는 사람 모두가 겪는 문제**입니다.
그리고 이런 방어 코드는 AI에게 요청해도 **먼저 알려 주지 않으면 절대 넣어 주지 않습니다.**
Spotfire의 출력 규약을 모르기 때문입니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` (마킹/필터로 제한해도 됨) |
| 입력 | `min_count` | Value (Integer) | 문서 속성 `MinCount` — 요약에 포함할 최소 계측 건수 |
| 출력 | `output` | Table | 설비별 요약 (안전하게 정리된 결과) |
| 출력 | `output_issue` | Table | `finalize()` 가 무엇을 고쳤는지 기록 |

> `output_issue` 를 텍스트 영역에 띄워 두면, 결과가 이상할 때
> **"내보내기 단계에서 무엇이 조정됐는지"** 를 바로 확인할 수 있습니다.

## 스크립트

```python
import pandas as pd

try:                                  # Spotfire 에는 번들되어 있다. 로컬은 pip install spotfire
    import spotfire
except ImportError:
    spotfire = None

# Spotfire 가 인정하는 타입 이름 (철자가 다르면 조용히 무시된다)
SPOTFIRE_TYPES = {"Boolean", "Integer", "LongInteger", "SingleReal", "Real",
                  "DateTime", "Date", "Time", "TimeSpan", "String", "Binary", "Currency"}
CONTAINERS = (list, tuple, set, dict)


def finalize(df, empty_row=None, types=None):
    """Spotfire 가 거부하지 않는 형태로 정리하고, 무엇을 고쳤는지 함께 돌려준다.

    값을 지어내지 않는다. 내보낼 수 있게 '모양'만 맞춘다.
    """
    df = df.copy()
    types = types or {}
    log = []

    def note(column, issue, action):
        log.append({"COLUMN": str(column), "ISSUE": issue, "ACTION": action})

    # 1) 인덱스는 Spotfire 로 전달되지 않는다 — 이름이 있으면 컬럼으로 꺼낸다
    if isinstance(df.index, pd.MultiIndex) or df.index.name is not None:
        names = list(df.index.names)
        df = df.reset_index()
        note(", ".join(str(n) for n in names), "인덱스에 담긴 키가 사라질 뻔함", "reset_index() 로 컬럼화")

    # 2) 컬럼명은 문자열이어야 한다
    if any(not isinstance(c, str) for c in df.columns):
        note("(여러 컬럼)", "컬럼명이 문자열이 아님", "str() 로 변환")
    df.columns = [str(c) for c in df.columns]
    df.columns.name = None

    # 3) 컬럼명 중복 — obj does not have unique column names
    if df.columns.duplicated().any():
        seen, renamed = {}, []
        for c in df.columns:
            seen[c] = seen.get(c, 0) + 1
            renamed.append(c if seen[c] == 1 else f"{c}_{seen[c]}")
        note(", ".join(sorted({c for c in df.columns[df.columns.duplicated()]})),
             "컬럼명 중복", "뒤에 _2, _3 을 붙여 구분")
        df.columns = renamed

    for col in df.columns:
        s = df[col]

        # 4) 셀 안의 list/dict — unknown type 'list' in column
        if any(isinstance(v, CONTAINERS) for v in s):
            df[col] = s.map(
                lambda v: ", ".join(map(str, v)) if isinstance(v, (list, tuple, set)) else
                (str(v) if isinstance(v, dict) else v)
            )
            note(col, "셀 안에 list/dict", "쉼표로 이어 붙인 문자열로 변환")
            s = df[col]

        # 5) 한 컬럼에 섞인 타입 — types in column do not match
        kinds = {type(v).__name__ for v in s.dropna()}
        if len(kinds) > 1:
            df[col] = s.map(lambda v: v if pd.isna(v) else str(v))
            note(col, f"타입이 섞임 ({', '.join(sorted(kinds))})", "astype(str) 로 통일")

        # 6) category 는 문자열로
        if str(s.dtype) == "category":
            df[col] = s.astype(str)
            note(col, "category dtype", "문자열로 변환")

    # 7) 0행 — 무엇을 넣을지는 호출하는 쪽이 정한다
    if len(df) == 0 and empty_row:
        df = pd.DataFrame([empty_row])
        note("(전체)", "결과가 0행", f"안내용 1행 삽입: {empty_row}")

    # 행 재배치는 여기서 끝낸다. 8) 의 타입 지정은 DataFrame 에 붙는 표시라서,
    # 그 뒤에 reset_index() 같은 새 DataFrame 을 만들면 지정이 사라진다.
    df = df.reset_index(drop=True)

    # 8) 전부 결측인 컬럼 — cannot determine type for column
    for col in df.columns:
        if not df[col].isna().all():
            continue
        wanted = types.get(col, "String")
        if wanted not in SPOTFIRE_TYPES:
            wanted = "String"
        if spotfire is not None:
            spotfire.set_spotfire_types(df, {col: wanted})
            note(col, "전부 결측", f"Spotfire 타입을 {wanted} 로 지정")
        else:
            df[col] = ""
            note(col, "전부 결측", "spotfire 패키지 없음 → 빈 문자열로 대체")

    issues = pd.DataFrame(log) if log else pd.DataFrame(
        [{"COLUMN": "-", "ISSUE": "없음", "ACTION": "조치 없이 그대로 내보냄"}]
    )
    return df, issues


# ------------------------------------------------------------------ 본 작업
df = input.copy()
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])

summary = (
    df.groupby(["EQP_ID", "STEP_DESC"])          # as_index=False 를 일부러 쓰지 않았다.
    .agg(                                        # finalize() 가 인덱스를 살려 내는지 보기 위함
        N=("THICKNESS", "size"),
        THICKNESS_MEAN=("THICKNESS", "mean"),
        THICKNESS_STD=("THICKNESS", "std"),
        LAST_MEAS=("MEAS_TIME", "max"),
    )
)
summary = summary[summary["N"] >= int(min_count)]
summary["THICKNESS_MEAN"] = summary["THICKNESS_MEAN"].round(3)
summary["THICKNESS_STD"] = summary["THICKNESS_STD"].round(3)

# 담당자가 나중에 채울 비고 컬럼 — 지금은 전부 비어 있다 (그대로 내보내면 오류)
summary["REVIEW_NOTE"] = None
summary["REVIEWED_AT"] = None

# empty_row 는 '결과가 0행일 때의 테이블 구조'를 정의한다.
# 정상 결과와 컬럼을 맞춰 두어야 Spotfire 쪽 시각화·컬럼 참조가 깨지지 않는다.
output, output_issue = finalize(
    summary,
    empty_row={"EQP_ID": "NO_DATA", "STEP_DESC": "-", "N": 0,
               "THICKNESS_MEAN": 0.0, "THICKNESS_STD": 0.0,
               "LAST_MEAS": pd.NaT, "REVIEW_NOTE": None, "REVIEWED_AT": None},
    types={"REVIEW_NOTE": "String", "REVIEWED_AT": "DateTime", "LAST_MEAS": "DateTime"},
)
```

## 핵심 포인트

- **`finalize()` 는 결과를 바꾸지 않고 "내보낼 수 있게만" 만듭니다.**
  값을 지어내지 않습니다. 전부 결측인 컬럼은 지우는 대신 **타입만 지정**하고,
  혼합 타입은 계산하는 대신 **문자열로 통일**합니다. 그리고 **무엇을 했는지 전부 기록**합니다.
- **0행 처리는 자동으로 하면 안 됩니다.** "데이터 없음" 한 줄을 넣을지, 빈 표를 낼지는
  분석마다 다릅니다. 그래서 `empty_row` 로 **호출하는 쪽이 정하게** 했습니다.
- `reset_index()` 는 **인덱스에 이름이 있을 때만** 합니다.
  의미 없는 0,1,2 인덱스까지 컬럼으로 만들면 지저분해집니다.
- `spotfire.set_spotfire_types()` 는 **틀린 타입 이름을 줘도 경고만 내고 넘어갑니다.**
  그래서 이 코드는 [문서에 있는 12개 타입 이름](../../syntax/07-spotfire-module/) 중에서만 고릅니다.
- **`empty_row` 는 정상 결과와 같은 컬럼을 갖도록 쓰세요.**
  0행일 때만 컬럼이 달라지면, 그 상황에서 Spotfire 시각화의 컬럼 참조가 깨집니다.

{: .주의 }
> ## `set_spotfire_types()` 는 **마지막에** 불러야 합니다
>
> 타입 지정은 **그 DataFrame 객체에 붙는 표시**입니다.
> 지정한 뒤에 `reset_index()` · `sort_values()` 처럼 **새 DataFrame 을 만드는 연산**을 하면
> 표시가 사라져서, 결국 원래의 "전부 결측" 오류로 돌아갑니다.
>
> ```python
> spotfire.set_spotfire_types(df, {"REMARK": "String"})
> output = df.reset_index(drop=True)      # ❌ 지정이 날아감
>
> df = df.reset_index(drop=True)
> spotfire.set_spotfire_types(df, {"REMARK": "String"})
> output = df                             # ✅
> ```
>
> `finalize()` 가 행 재배치를 먼저 끝내고 타입 지정을 **맨 마지막에** 하는 이유입니다.

{: .주의 }
> `finalize()` 는 **마지막 한 번만** 부르세요.
> 중간 결과에 걸면 문자열로 바뀐 컬럼에 다시 산술 연산을 하려다 오류가 납니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수의 '출력 안전장치' 함수를 만들어 줘.

finalize(df, empty_row=None, types=None) -> (정리된 DataFrame, 조치 내역 DataFrame)

Spotfire 로 내보낼 때 실패하는 조건들을 아래 순서로 처리할 것:
1. 인덱스에 이름이 있거나 MultiIndex 면 reset_index()
2. 컬럼명을 전부 문자열로, columns.name 은 None 으로
3. 컬럼명이 중복이면 _2, _3 을 붙여 유일하게
4. 셀에 list/tuple/set/dict 이 있으면 ", ".join 으로 문자열화
5. 한 컬럼에 여러 파이썬 타입이 섞여 있으면 astype(str)
6. category dtype 은 문자열로
7. 0행이고 empty_row(dict)가 주어지면 그 한 줄을 넣기
8. 전부 결측인 컬럼은 spotfire.set_spotfire_types 로 타입 지정
   (types 로 지정된 게 있으면 그것을, 없으면 "String")
9. 각 조치를 (COLUMN, ISSUE, ACTION) 로 기록해 두 번째 값으로 반환

조건: inplace 쓰지 말 것. 값을 임의로 지어내지 말 것.
spotfire 패키지가 없는 환경에서도 죽지 않게 할 것.
```

## 확인 & 응용

- 일부러 깨뜨려 보세요. `min_count` 를 아주 크게(예: `99999`) 주면 **결과가 0행**이 됩니다.
  `finalize()` 가 없으면 오류, 있으면 "데이터 없음" 한 줄이 나옵니다.
- **응용 1**: `finalize()` 를 라이브러리 데이터 함수로 저장하지 말고,
  팀 표준 **코드 스니펫**으로 공유하세요. 데이터 함수는 함수를 import 할 수 없습니다.
- **응용 2**: `output_issue` 가 비어 있지 않으면 Spotfire에서 **경고 아이콘을 띄우는**
  텍스트 영역 규칙을 만들어 두면, 조용한 데이터 품질 저하를 놓치지 않습니다.
- **응용 3**: [25번 진단기](../25-input-type-doctor/)가 입구, 이 예제가 출구입니다.
  둘을 함께 쓰면 데이터 함수의 양 끝이 모두 방어됩니다.

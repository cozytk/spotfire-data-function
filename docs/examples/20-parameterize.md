---
title: 20. 문서 속성으로 파라미터화 — 한 번 만들어 계속 쓰는 데이터 함수
parent: 예제 모음
nav_order: 20
---

# 20. 문서 속성으로 파라미터화 — 한 번 만들어 계속 쓰는 데이터 함수
{: .no_toc }

**난이도** ★★★ · **Level 4 · 통계·자동화·Spotfire 고유 기능**

그룹 컬럼·집계 방식·기간·임계값을 전부 Value 입력으로 받아, 코드를 고치지 않고 화면에서 조작하는 범용 요약 함수를 만듭니다.

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/20_parameterize.py)

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
| 입력 | `group_cols` | Value | 문서 속성 (예: `EQP_ID;STEP_DESC`) |
| 입력 | `value_col` | Value | 문서 속성 (예: `THICKNESS`) |
| 입력 | `agg_list` | Value | 문서 속성 (예: `mean;std;median;count`) |
| 입력 | `date_from` | Value | 문서 속성 (예: `2026-03-03`) |
| 입력 | `date_to` | Value | 문서 속성 (예: `2026-03-08`) |
| 입력 | `threshold` | Value | 문서 속성 (예: `3.0`) |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_meta` | Table | 새 데이터 테이블 |

---

## 시나리오

데이터 함수를 만들 때마다 "이번엔 설비별로", "이번엔 공정별로", "이번엔 CD 기준으로" 요청이 옵니다.
매번 코드를 복사해서 컬럼명만 바꾸면 **비슷하지만 조금씩 다른 함수가 20개** 생깁니다.

해법: **바뀌는 것을 전부 입력 파라미터로 빼는 것.**
사용자는 텍스트 영역의 드롭다운/슬라이더로 조작하고, 코드는 하나만 유지합니다.

## Spotfire 데이터 함수의 특징적인 입력 방식

이 예제는 **Spotfire에서만 가능한 부분**입니다. 입력 파라미터는 세 가지 타입이 있고,
각각 연결할 수 있는 대상이 다릅니다.

| 타입 | Python에서의 모습 | 연결 가능한 대상 |
|---|---|---|
| **Value** | `str`, `int`, `float`, `bool` | 문서 속성, 컬럼 속성, 단일 값 표현식 |
| **Column** | `pandas.Series` | 데이터 테이블의 한 컬럼, 계산된 표현식 |
| **Table** | `pandas.DataFrame` | 데이터 테이블 전체 또는 선택한 컬럼들 |

그리고 Table/Column 입력에는 **"입력 제한(Limit by)"** 을 걸 수 있습니다.

- **마킹(Marking)** — 사용자가 차트에서 선택한 행만 (→ [21번 예제](../21-marking-compare/))
- **필터링(Filtering)** — 현재 필터가 적용된 행만
- 둘 다 지정하면 **교집합**이 전달됩니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 문서 속성 / UI 컨트롤 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 입력 | `group_cols` | Value (String) | `GroupCols` — 목록 상자 (세미콜론 구분) |
| 입력 | `value_col` | Value (String) | `ValueCol` — 드롭다운 |
| 입력 | `agg_list` | Value (String) | `AggList` — 다중 선택 목록 |
| 입력 | `date_from` / `date_to` | Value (String) | 날짜 선택 컨트롤 |
| 입력 | `threshold` | Value (Real) | `Threshold` — 슬라이더 |
| 출력 | `output` | Table | 요약 결과 |
| 출력 | `output_meta` | Table | 실행 조건 기록 |

> **텍스트 영역 → 속성 컨트롤 삽입**으로 각 문서 속성에 컨트롤을 붙이고,
> 데이터 함수 속성에서 **"입력이 변경되면 자동으로 다시 계산"** 을 켜면
> 사용자가 값을 바꾸는 즉시 결과가 갱신됩니다.

## 스크립트

```python
import numpy as np
import pandas as pd

df = input.copy()

# --- 1) 입력값 파싱 및 검증 ------------------------------------------------
# Spotfire 의 Value 입력은 리스트를 못 넘기므로 "A;B;C" 문자열로 받아 쪼갠다
requested_groups = [c.strip() for c in str(group_cols).split(";") if c.strip()]
group_list = [c for c in requested_groups if c in df.columns]
if not group_list:
    group_list = ["EQP_ID"]  # 유효한 컬럼이 하나도 없으면 기본값

value = str(value_col).strip()
if value not in df.columns or not pd.api.types.is_numeric_dtype(df[value]):
    value = "THICKNESS"

VALID_AGGS = ["mean", "std", "median", "count", "min", "max", "sum"]
agg_funcs = [a.strip() for a in str(agg_list).split(";") if a.strip() in VALID_AGGS]
if not agg_funcs:
    agg_funcs = ["mean", "std", "count"]

# --- 2) 기간 필터 (값이 비어 있으면 적용하지 않음) --------------------------
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"], errors="coerce")
n_before = len(df)
if str(date_from).strip():
    df = df[df["MEAS_TIME"] >= pd.Timestamp(str(date_from))]
if str(date_to).strip():
    df = df[df["MEAS_TIME"] < pd.Timestamp(str(date_to)) + pd.Timedelta(days=1)]

# --- 3) 동적 집계 ----------------------------------------------------------
if len(df) == 0:
    res = pd.DataFrame([{c: "NO_DATA" for c in group_list}])
    for a in agg_funcs:
        res[f"{value}_{a}"] = 0.0
    res["ALERT"] = "데이터 없음"
else:
    res = df.groupby(group_list, as_index=False)[value].agg(agg_funcs)
    # 집계 결과 컬럼명을 "<대상컬럼>_<함수명>" 으로 정리
    res = res.rename(columns={a: f"{value}_{a}" for a in agg_funcs})

    std_col = f"{value}_std"
    if std_col in res.columns:
        res["ALERT"] = np.where(res[std_col] > float(threshold), "주의", "정상")
    else:
        res["ALERT"] = "정상"

    num_cols = [c for c in res.columns if c.startswith(f"{value}_")]
    res[num_cols] = res[num_cols].round(4)

# --- 4) 실행 조건 기록 ------------------------------------------------------
meta = pd.DataFrame(
    [
        {"ITEM": "그룹 컬럼", "VALUE": ", ".join(group_list)},
        {"ITEM": "집계 대상", "VALUE": value},
        {"ITEM": "집계 함수", "VALUE": ", ".join(agg_funcs)},
        {"ITEM": "기간", "VALUE": f"{date_from} ~ {date_to}"},
        {"ITEM": "임계값", "VALUE": str(threshold)},
        {"ITEM": "입력 행 수", "VALUE": f"{n_before:,}"},
        {"ITEM": "필터 후 행 수", "VALUE": f"{len(df):,}"},
        {"ITEM": "결과 그룹 수", "VALUE": f"{len(res):,}"},
        {"ITEM": "무시된 입력", "VALUE": ", ".join(set(requested_groups) - set(group_list)) or "없음"},
    ]
)

output = res
output_meta = meta
```

## 핵심 포인트

- **Spotfire의 Value 입력은 리스트를 전달하지 못합니다.** 그래서 `"A;B;C"` 처럼 문자열로 받아
  `split(";")` 로 나누는 것이 표준 관용구입니다. 문서 속성 목록 상자와도 잘 맞습니다.
- **입력값 검증을 반드시 하세요.** 사용자가 존재하지 않는 컬럼명을 넣으면 `KeyError` 로 죽습니다.
  존재하는 컬럼만 남기고, 하나도 없으면 **기본값으로 대체**하는 것이 사용자 경험상 훨씬 낫습니다.
- **`output_meta` 로 실행 조건을 남기세요.** "이 표는 어떤 기간, 어떤 조건으로 뽑은 거죠?"라는 질문에
  화면 안에서 바로 답할 수 있습니다. 보고서 캡처 시에도 유용합니다.
- Value 입력의 Spotfire 타입과 Python 타입은 자동 매핑되지만, **문서 속성이 String이면 숫자도 문자열로 들어옵니다.**
  `float(threshold)` 처럼 명시적으로 변환하는 습관을 들이세요.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 재사용 가능한 '범용 그룹 요약' 함수를 만들어줘.
입력:
- input : DataFrame
- group_cols : 문자열, 세미콜론으로 구분된 그룹 컬럼 목록 (예 "EQP_ID;STEP_DESC")
- value_col  : 문자열, 집계 대상 컬럼명
- agg_list   : 문자열, 세미콜론 구분 집계 함수 목록 (mean;std;median;count;min;max)
- date_from, date_to : 문자열 날짜 (YYYY-MM-DD), MEAS_TIME 기준 필터
- threshold  : float, 그룹 표준편차가 이 값을 넘으면 ALERT 표시

요구사항:
1. 모든 입력값을 검증할 것. 없는 컬럼명/집계함수는 무시하고, 전부 유효하지 않으면 기본값 사용
2. 날짜 필터는 값이 비어 있으면 적용하지 않음
3. 집계 결과 컬럼명은 "<value_col>_<함수명>" 형식
4. 그룹 표준편차 > threshold 이면 ALERT='주의', 아니면 '정상'
5. 실행 조건(적용된 그룹/기간/행수/실행시각)을 output_meta 로 함께 출력
예외가 나도 데이터 함수가 죽지 않게 방어적으로 작성해줘. 출력: output, output_meta
```

## 확인 & 응용

- `group_cols` 를 `LOT_ID` 로 바꿔 실행해 보세요. **코드 수정 없이** 랏 단위 요약이 나옵니다.
- **응용**: `value_col` 드롭다운의 선택지를 컬럼 목록에서 자동 생성하려면
  별도의 작은 데이터 함수로 "숫자 컬럼 목록" 테이블을 만들어 목록 상자에 연결하세요.

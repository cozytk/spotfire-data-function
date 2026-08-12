---
title: 04. 두 테이블 조인 후 조건별로 여러 테이블로 분리 출력
parent: 예제 모음
nav_order: 4
---

# 04. 두 테이블 조인 후 조건별로 여러 테이블로 분리 출력
{: .no_toc }

**난이도** ★★☆ · **Level 1 · 정제 기초**

merge + indicator 로 조인 실패까지 진단하고, 결과를 공정별 3개 테이블로 쪼개 한 번에 내보냅니다. 기존 실습 스크립트의 개선판.

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv), [`lot_master.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/lot_master.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/04_join_and_split.py)

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

### 파라미터 요약
{: .no_toc }

| 구분 | 이름 | 타입 | 연결 |
|---|---|---|---|
| 입력 | `input1` | Table | `fab_measurement.csv` |
| 입력 | `input2` | Table | `lot_master.csv` |
| 출력 | `output1` | Table | 새 데이터 테이블 |
| 출력 | `output2` | Table | 새 데이터 테이블 |
| 출력 | `output3` | Table | 새 데이터 테이블 |
| 출력 | `output_unmatched` | Table | 새 데이터 테이블 |

---

## 시나리오

계측 이력(`fab_measurement`)에 LOT 마스터(`lot_master`)의 제품·라인 정보를 붙이고,
후속 분석 담당이 다른 공정(`PC` / `RMG` / `CBCMP`)별로 테이블을 나눠 달라고 합니다.
덤으로 **조인에 실패한 LOT**도 확인해야 합니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire의 "데이터 테이블 추가 → 열 추가"로 조인은 됩니다. 하지만
  **조인 실패 행을 찾아내는 것**은 별도 작업이고(빈 값 필터), 매번 수동입니다.
- **하나의 테이블을 조건별로 N개로 쪼개 새 데이터 테이블로 만드는 기능은 없습니다.**
  (필터링 스키마로 뷰를 나눌 수는 있지만, 물리적으로 분리된 테이블은 아닙니다.)
- 데이터 함수는 **출력 파라미터를 원하는 만큼** 선언할 수 있어 한 번 실행으로 여러 테이블을 만듭니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input1` | Table | `fab_measurement` |
| 입력 | `input2` | Table | `lot_master` |
| 출력 | `output1` | Table | `PC 공정` |
| 출력 | `output2` | Table | `RMG 공정` |
| 출력 | `output3` | Table | `CMP 계열(그 외)` |
| 출력 | `output_unmatched` | Table | `조인 실패 LOT` |

## 스크립트

```python
import pandas as pd

meas = input1.copy()
lot = input2.copy()

KEY = "JOIN_ID"

# 1) 조인 키 정규화 : 공백/대소문자/타입 불일치가 조인 실패의 대부분
for d in (meas, lot):
    d[KEY] = d[KEY].astype(str).str.strip().str.upper()

# 2) 오른쪽 테이블 키 중복 점검 — 중복이 있으면 조인 후 행이 불어난다
if lot[KEY].duplicated().any():
    lot = lot.drop_duplicates(subset=[KEY], keep="first")

# 3) left join + 매칭 여부 표시
df = meas.merge(lot, on=KEY, how="left", indicator=True, suffixes=("", "_LOT"))

unmatched = df[df["_merge"] == "left_only"].drop(columns=["_merge"])
df = df[df["_merge"] == "both"].drop(columns=["_merge"])

# 4) 값 정리
df["IS_DEFECT"] = df["IS_DEFECT"].replace({"REAL": "TRUE"})
df = df.fillna({"SIZE_Y": 0.1})

# 5) 공정별 분리 — 마지막은 '그 외 전부'로 받아 누락을 방지
is_pc = df["STEP_DESC"] == "PC"
is_rmg = df["STEP_DESC"] == "RMG"

df1 = df[is_pc]
df2 = df[is_rmg]
df3 = df[~(is_pc | is_rmg)]


def safe(frame, like):
    """빈 결과를 그대로 내보내면 Spotfire 에서 오류가 날 수 있으므로 최소 1행을 보장한다.

    이때 '전부 결측인 컬럼'을 만들면 Spotfire 가 타입을 결정하지 못해 또 오류가 나므로,
    컬럼 dtype 에 맞는 기본값을 채워 넣는 것이 안전하다.
    """
    if len(frame) > 0:
        return frame.reset_index(drop=True)
    row = {}
    for col, dtype in like.dtypes.items():
        if pd.api.types.is_numeric_dtype(dtype):
            row[col] = 0
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            row[col] = pd.Timestamp("1970-01-01")
        else:
            row[col] = "NO_DATA"
    return pd.DataFrame([row])


output1 = safe(df1, df)
output2 = safe(df2, df)
output3 = safe(df3, df)
output_unmatched = safe(unmatched, df)
```

## 핵심 포인트

- **조인 전에 키를 점검**하세요. 실무 조인 실패 원인 1~3위는 전부 시시합니다.
  ① 앞뒤 공백 ② 대소문자 ③ 숫자/문자 타입 불일치. `.astype(str).str.strip().str.upper()` 로 정규화하고 시작합니다.
- `how="left"` + `indicator=True` 를 쓰면 `_merge` 컬럼에 `both` / `left_only` 가 찍혀
  **몇 건이 매칭 안 됐는지 즉시** 알 수 있습니다. 진단이 끝나면 이 컬럼은 지워서 내보냅니다.
- 조인 후 **행 수가 늘었다면** 오른쪽 테이블에 키가 중복된 것입니다.
  `input2["JOIN_ID"].duplicated().any()` 로 먼저 확인하세요. (실무 사고 1위)
- 분리 조건에 **`isin()` 과 "그 외 전부"** 를 함께 쓰면 어떤 행도 누락되지 않습니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수를 작성해줘.
입력: input1(계측이력), input2(LOT마스터). 둘 다 pandas DataFrame. 조인 키는 JOIN_ID.
요구:
1. 조인 키의 공백/대소문자를 정규화한 뒤 left join
2. 조인 실패 행(매칭 안 된 것)은 output_unmatched 로 분리
3. 조인 후 행 수가 늘어나는지(오른쪽 키 중복) 검사해서, 중복이면 첫 행만 사용
4. STEP_DESC 가 'PC' 인 것 -> output1, 'RMG' -> output2, 나머지 전부 -> output3
5. 각 출력이 빈 DataFrame 이 되지 않도록, 비면 컬럼 구조만 유지한 1행짜리 안내 행을 넣어줘
전부 output1..output3, output_unmatched 변수에 할당.
```

> 5번 요구사항이 중요합니다. Spotfire는 **빈 테이블을 출력하면 오류가 나거나 테이블이 사라질 수 있습니다.**

## 확인 & 응용

- `output_unmatched` 가 0행이면 조인이 깨끗하다는 뜻입니다.
- **응용**: 분할 기준을 하드코딩하지 말고 `Value` 입력으로 받아 보세요.
  (`split_col="STEP_DESC"`, `split_values="PC;RMG"`)

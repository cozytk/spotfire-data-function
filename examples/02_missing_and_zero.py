'''---
title: 결측치·0값 행 정리 (안전하게)
level: 1
difficulty: ★☆☆
summary: dropna 3종 세트. "0이 있는 행 지우기"를 전체 컬럼에 적용하면 왜 위험한지, 어떻게 고쳐야 하는지까지.
data: [fab_measurement.csv]
inputs:
  input:
    file: fab_measurement.csv
outputs: [output, output_report]
---
## 시나리오

계측 데이터에는 세 가지 "구멍"이 있습니다.

- `CD`, `THICKNESS` 가 비어 있는 행 (계측 실패)
- `PRESSURE` 가 `0` 인 행 (센서 미취득 — 실제로 압력이 0일 리 없음)
- 어느 컬럼이든 비어 있는 행

분석 목적에 따라 무엇을 지울지가 달라지므로, **왜 그렇게 지웠는지 근거를 남기는 것**까지가 한 세트입니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- 필터로 숨기는 건 가능하지만 **"행 삭제"는 되지 않습니다.** 다운스트림 집계·조인에는 여전히 따라다닙니다.
- "여러 컬럼 중 하나라도 비면 제외" 같은 조건은 표현식으로 쓰면
  `[A] is null or [B] is null or ...` 처럼 컬럼 수만큼 길어집니다. 컬럼이 200개면 불가능합니다.
- 지운 근거(무엇을 몇 건 지웠는지)를 남기려면 별도 시각화를 또 만들어야 합니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 출력 | `output` | Table | 정제된 데이터 테이블 |
| 출력 | `output_report` | Table | 정제 리포트 (단계별 제거 건수) |

## 스크립트

{{CODE}}

## 핵심 포인트

- **`df.dropna()` 는 "한 컬럼이라도 비면 삭제"** 입니다. 기본값이 `how="any"` 라는 걸 모르면
  멀쩡한 데이터의 절반이 사라집니다. 반드시 `subset=` 으로 대상 컬럼을 좁히세요.
- 기존 실습에 나오는 `df[(df != 0).all(axis=1)]` 은 **모든 컬럼**을 검사합니다.
  `WAFER_NO`, `PARTICLE_CNT` 처럼 **0이 정상값인 컬럼까지 지워 버리는** 대표적인 사고입니다.
  → 반드시 "0이 결측을 의미하는 컬럼"만 지정해서 검사하세요.
- 문자열 컬럼의 빈 문자열 `""` 은 `NaN` 이 아닙니다. 필요하면 `replace("", np.nan)` 로 먼저 통일하세요.
- 몇 건이 왜 지워졌는지를 **리포트 테이블로 함께 출력**하면 리뷰가 통과됩니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수를 작성해줘.
입력 input(DataFrame) 컬럼: LOT_ID, WAFER_NO, STEP_DESC, THICKNESS, CD, TEMP, PRESSURE, PARTICLE_CNT
정제 규칙:
- THICKNESS 또는 CD 가 결측인 행 삭제
- PRESSURE 가 0 인 행 삭제 (0은 센서 미취득을 의미). 단 PARTICLE_CNT 의 0 은 정상값이므로 남길 것.
- 각 단계에서 몇 건이 제거됐는지 요약한 DataFrame 도 만들 것 (컬럼: STEP, REMOVED_ROWS, REMAIN_ROWS)
출력: output(정제결과), output_report(요약)
inplace 는 쓰지 말고, 전체 컬럼을 일괄 검사하는 방식은 쓰지 마.
```

> 마지막 한 줄("전체 컬럼 일괄 검사 금지")이 AI가 `df[(df != 0).all(axis=1)]` 같은 위험한 코드를 뱉는 것을 막아 줍니다.
> **하지 말아야 할 것을 함께 적는 것**이 프롬프트 품질을 크게 올립니다.

## 확인 & 응용

- `output_report` 를 막대 그래프로 그려 어느 단계에서 가장 많이 빠졌는지 보세요.
- **응용**: 제거 대신 대치(imputation)가 맞는 상황도 많습니다 → [08번 예제](../08-impute-smart/) 로.
'''
import numpy as np
import pandas as pd

df = input.copy()
report = []


def log(step_name, before, after):
    report.append({"STEP": step_name, "REMOVED_ROWS": before - len(after), "REMAIN_ROWS": len(after)})
    return after


n0 = len(df)

# 0) 문자열 컬럼의 빈 문자열을 결측으로 통일 (Spotfire 에서 넘어온 빈 값 대비)
obj_cols = df.select_dtypes(include="object").columns
df[obj_cols] = df[obj_cols].replace(r"^\s*$", np.nan, regex=True)

# 1) 핵심 계측값이 비어 있는 행 삭제 (subset 으로 대상을 반드시 좁힌다)
before = len(df)
df = df.dropna(subset=["THICKNESS", "CD"])
df = log("THICKNESS/CD 결측 제거", before, df)

# 2) 0 이 '결측'을 뜻하는 컬럼만 골라서 0 행 삭제
#    (PARTICLE_CNT, WAFER_NO 처럼 0/1 이 정상값인 컬럼은 절대 포함하지 않는다)
ZERO_IS_MISSING = ["PRESSURE", "TEMP"]
before = len(df)
zero_mask = (df[ZERO_IS_MISSING] == 0).any(axis=1)
df = df[~zero_mask]
df = log("PRESSURE/TEMP 0값 제거", before, df)

# 3) 그래도 남은 결측이 문제라면 대상 컬럼을 좁혀 한 번 더
before = len(df)
df = df.dropna(subset=["EQP_ID", "STEP_DESC"])
df = log("키 컬럼 결측 제거", before, df)

output = df.reset_index(drop=True)
output_report = pd.DataFrame(
    [{"STEP": "원본", "REMOVED_ROWS": 0, "REMAIN_ROWS": n0}] + report
)

'''---
title: 마킹(Marking) 입력 활용 — 선택한 구간 vs 나머지 비교
level: 4
difficulty: ★★★
summary: Spotfire에서만 가능한 입력 방식. 사용자가 차트에서 드래그로 고른 행을 그대로 함수의 입력으로 받아 "이 구간이 뭐가 다른가"를 즉시 계산합니다.
data: [fab_measurement.csv]
inputs:
  input_marked:
    file: fab_measurement.csv
    query: "EQP_ID == 'ETC01' and THICKNESS > 148"
  input_all:
    file: fab_measurement.csv
outputs: [output, output_profile]
---
## 시나리오

관리도에서 이상해 보이는 구간을 마우스로 드래그합니다. 그리고 묻습니다.

> **"내가 지금 선택한 이 웨이퍼들은, 나머지와 뭐가 다른가?"**

- 어느 설비/챔버/작업자에 몰려 있는가?
- 어떤 수치가 유의하게 다른가?

이 질문에 **클릭 한 번으로** 답하는 것이 마킹 입력의 진가입니다.
이것은 **Spotfire 데이터 함수만의 고유 기능**으로, 다른 분석 도구에서는 흉내 내기 어렵습니다.

## 이 예제의 진짜 주제: 입력 제한(Limit by)

같은 데이터 테이블을 **두 개의 입력 파라미터**로 받되, 제한 조건만 다르게 겁니다.

| 파라미터 | 타입 | 입력 제한 |
|---|---|---|
| `input_marked` | Table | ✅ **마킹**: `Marking` 선택 |
| `input_all` | Table | 제한 없음 (또는 필터링만) |

설정 화면(데이터 함수 편집 → 입력 파라미터 → **입력 제한**)에서

- **마킹으로 제한**: 지정한 마킹에 포함된 행만 전달
- **필터링으로 제한**: 현재 필터 조건에 맞는 행만 전달
- **둘 다 선택**: 교집합

> ⚠️ **함정**: 아무것도 마킹하지 않으면 `input_marked` 는 **0행**으로 들어옵니다.
> 이때 코드가 죽지 않도록 **맨 앞에서 `len(...) == 0` 을 반드시 확인**해야 합니다.
> 마킹 기반 데이터 함수에서 발생하는 오류의 대부분이 이것입니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input_marked` | Table | `fab_measurement` (마킹으로 제한) |
| 입력 | `input_all` | Table | `fab_measurement` (제한 없음) |
| 출력 | `output` | Table | 숫자 컬럼 비교 |
| 출력 | `output_profile` | Table | 범주형 컬럼 쏠림 비교 |

> 데이터 함수 속성에서 **"입력이 변경되면 자동으로 다시 계산"** 을 켜 두면
> 마킹을 바꿀 때마다 결과가 실시간으로 갱신됩니다. 이게 켜져 있어야 이 예제가 살아납니다.

## 스크립트

{{CODE}}

## 핵심 포인트

- **빈 마킹 방어가 1순위입니다.** `if len(marked) == 0:` 으로 시작해 안내 테이블을 반환하세요.
  오류 대화상자 대신 "차트에서 데이터를 선택하세요"라는 안내가 뜨는 것과는 사용자 경험이 하늘과 땅 차이입니다.
- 비교 대상은 **마킹 vs 전체**가 아니라 **마킹 vs 나머지(마킹되지 않은 행)** 여야 합니다.
  전체에는 마킹된 행이 포함되어 있어 차이가 희석됩니다. 여기서는 인덱스 키로 나머지를 분리했습니다.
- 범주형은 **비율 차이(lift)** 로 봅니다. "마킹 구간에서 CHAMBER=B 비중이 전체의 3배" 같은 문장이
  바로 원인 가설이 됩니다.
- 숫자형은 표준화된 차이(Cohen's d 유사 지표)로 정렬하면 **가장 크게 다른 항목이 맨 위**에 옵니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수를 작성해줘. 마킹 비교 분석이야.
입력:
- input_marked : 사용자가 마킹한 행들 (DataFrame, 0행일 수 있음)
- input_all    : 전체 행 (DataFrame)

1. input_marked 가 비어 있으면 오류 대신 '차트에서 데이터를 선택하세요' 안내 1행 테이블을 반환
2. 전체에서 마킹된 행을 제외한 '나머지' 집합을 만들어 비교 (LOT_ID, WAFER_NO, STEP_DESC, MEAS_TIME 조합을 키로)
3. 숫자 컬럼별로 마킹평균/나머지평균/차이/차이비율(%)/표준화차이 계산 후
   표준화차이 절대값 내림차순 정렬
4. 범주형 컬럼(EQP_ID, STEP_DESC, CHAMBER, IS_DEFECT)별로 마킹 구간의 값 분포와
   나머지 분포를 비교해 LIFT(마킹비율/나머지비율) 계산, LIFT 2 이상은 '쏠림' 표시
5. 결과는 output(숫자 비교), output_profile(범주 비교)
빈 입력, 0으로 나누기, 컬럼 없음 상황을 모두 방어해줘.
```

## 확인 & 응용

- 관리도에서 이상 구간을 드래그 → `output_profile` 에서 `LIFT` 가 높은 항목을 보세요. 원인 후보가 바로 나옵니다.
- **응용**: 마킹 두 개(`Marking A`, `Marking B`)를 각각 입력으로 받아 **A/B 구간 직접 비교**로 확장하세요.
- **응용**: 차이가 큰 항목에 대해 [18번 예제](../18-group-test-anova/)의 t-test를 붙이면
  "쏠림이 우연인지"까지 답할 수 있습니다.
'''
import numpy as np
import pandas as pd

marked = input_marked.copy()
all_df = input_all.copy()

CAT_COLS = ["EQP_ID", "STEP_DESC", "CHAMBER", "IS_DEFECT"]
KEY_COLS = ["LOT_ID", "WAFER_NO", "STEP_DESC", "MEAS_TIME"]

# --- 0) 빈 마킹 방어 : 마킹 기반 데이터 함수의 필수 관문 --------------------
if len(marked) == 0:
    output = pd.DataFrame(
        [{"COLUMN": "안내", "MARKED_MEAN": 0.0, "REST_MEAN": 0.0, "DIFF": 0.0,
          "DIFF_PCT": 0.0, "STD_DIFF": 0.0, "NOTE": "차트에서 데이터를 마킹(선택)하세요"}]
    )
    output_profile = pd.DataFrame(
        [{"COLUMN": "안내", "VALUE": "-", "MARKED_PCT": 0.0, "REST_PCT": 0.0,
          "LIFT": 0.0, "FLAG": "차트에서 데이터를 마킹(선택)하세요"}]
    )
else:
    # --- 1) '나머지' 집합 만들기 (전체 - 마킹) ------------------------------
    def make_key(d):
        return d[KEY_COLS].astype(str).agg("|".join, axis=1)

    marked_keys = set(make_key(marked))
    rest = all_df[~make_key(all_df).isin(marked_keys)]

    # --- 2) 숫자 컬럼 비교 --------------------------------------------------
    num_cols = [
        c for c in marked.select_dtypes(include="number").columns
        if c in rest.columns and c not in ("WAFER_NO",)
    ]
    rows = []
    for c in num_cols:
        m, r = marked[c].dropna(), rest[c].dropna()
        if len(m) == 0 or len(r) == 0:
            continue
        pooled = np.sqrt((m.var(ddof=1) + r.var(ddof=1)) / 2)
        rows.append(
            {
                "COLUMN": c,
                "MARKED_N": len(m), "REST_N": len(r),
                "MARKED_MEAN": round(float(m.mean()), 4), "REST_MEAN": round(float(r.mean()), 4),
                "DIFF": round(float(m.mean() - r.mean()), 4),
                "DIFF_PCT": round(float((m.mean() - r.mean()) / r.mean() * 100), 2) if r.mean() != 0 else np.nan,
                "STD_DIFF": round(float((m.mean() - r.mean()) / pooled), 4) if pooled > 0 else np.nan,
            }
        )
    num_cmp = pd.DataFrame(rows)
    if num_cmp.empty:
        num_cmp = pd.DataFrame([{"COLUMN": "없음", "MARKED_N": 0, "REST_N": 0, "MARKED_MEAN": 0.0,
                                 "REST_MEAN": 0.0, "DIFF": 0.0, "DIFF_PCT": 0.0, "STD_DIFF": 0.0}])
    else:
        num_cmp["ABS_STD_DIFF"] = num_cmp["STD_DIFF"].abs()
        num_cmp = num_cmp.sort_values("ABS_STD_DIFF", ascending=False)
        num_cmp["NOTE"] = np.where(num_cmp["ABS_STD_DIFF"] >= 0.8, "큰 차이",
                                   np.where(num_cmp["ABS_STD_DIFF"] >= 0.5, "중간 차이", ""))

    # --- 3) 범주형 쏠림 비교 (LIFT) ----------------------------------------
    prof_rows = []
    for c in CAT_COLS:
        if c not in marked.columns:
            continue
        m_pct = marked[c].value_counts(normalize=True)
        r_pct = rest[c].value_counts(normalize=True)
        for value in m_pct.index:
            mp = float(m_pct.get(value, 0)) * 100
            rp = float(r_pct.get(value, 0)) * 100
            prof_rows.append(
                {
                    "COLUMN": c, "VALUE": str(value),
                    "MARKED_PCT": round(mp, 2), "REST_PCT": round(rp, 2),
                    "LIFT": round(mp / rp, 2) if rp > 0 else np.nan,
                    "MARKED_CNT": int((marked[c] == value).sum()),
                }
            )
    profile = pd.DataFrame(prof_rows)
    profile["FLAG"] = np.select(
        [profile["LIFT"] >= 2, profile["LIFT"] <= 0.5],
        ["쏠림(과다)", "쏠림(과소)"],
        default="",
    )
    profile = profile.sort_values("LIFT", ascending=False)

    output = num_cmp.reset_index(drop=True)
    output_profile = profile.reset_index(drop=True)

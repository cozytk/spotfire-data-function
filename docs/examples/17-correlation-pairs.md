---
title: "17. 상관 매트릭스를 "쌍(pair) 테이블"로 뒤집기"
parent: 예제 모음
nav_order: 17
---

# 17. 상관 매트릭스를 "쌍(pair) 테이블"로 뒤집기
{: .no_toc }

**난이도** ★★☆ · **Level 4 · 통계·자동화·Spotfire 고유 기능**

20×20 상관 매트릭스에서 의미 있는 상관쌍만 뽑아 랭킹 테이블로 만듭니다. 센서가 많을수록 강력해집니다.

사용 데이터: [`equipment_sensor_wide.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/equipment_sensor_wide.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/17_correlation_pairs.py)

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

### 파라미터 요약
{: .no_toc }

| 구분 | 이름 | 타입 | 연결 |
|---|---|---|---|
| 입력 | `input` | Table | `equipment_sensor_wide.csv` |
| 입력 | `min_abs_r` | Value | 문서 속성 (예: `0.7`) |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_pairs` | Table | 새 데이터 테이블 |

---

## 시나리오

센서가 20개면 상관쌍은 190개, 50개면 1,225개입니다.
히트맵을 눈으로 훑는 방식은 센서가 늘어나는 순간 무너집니다.

필요한 건 **"상관계수 절대값이 0.7 이상인 쌍만, 강한 순서대로"** 정렬된 목록입니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire에 상관 히트맵은 있지만 **결과가 데이터가 아닙니다.** 정렬·필터·조인이 안 됩니다.
- "상위 20개 쌍만" 같은 요구를 표현할 방법이 없습니다.
- 센서 컬럼이 추가되면 시각화 설정을 다시 해야 합니다.
- pandas는 `df.corr()` 한 줄로 매트릭스를 만들고, **위쪽 삼각형만 남겨 Long으로 뒤집으면** 끝입니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `equipment_sensor_wide` |
| 입력 | `min_abs_r` | Value (Real) | 문서 속성 `MinAbsR` (기본 0.7) |
| 출력 | `output` | Table | 전체 상관쌍 (Long, 히트맵용) |
| 출력 | `output_pairs` | Table | 임계값 이상 강한 상관쌍 랭킹 |

## 스크립트

```python
import numpy as np
import pandas as pd

df = input.copy()

EXCLUDE = ["TIMESTAMP", "EQP_ID"]
MIN_N = 30

num_cols = [c for c in df.select_dtypes(include="number").columns if c not in EXCLUDE]

rows = []
for eqp, block in df.groupby("EQP_ID"):
    sub = block[num_cols].dropna(how="all", axis=1)
    if len(sub) < MIN_N or sub.shape[1] < 2:
        continue

    corr = sub.corr(method="pearson")

    # 상삼각행렬만 남긴다 : 대각선(r=1)과 (A,B)/(B,A) 중복 제거
    mask = np.triu(np.ones(corr.shape, dtype=bool), k=1)
    upper = corr.where(mask)

    long_block = upper.stack().reset_index()
    long_block.columns = ["VAR1", "VAR2", "R"]
    long_block.insert(0, "EQP_ID", eqp)
    long_block["N"] = len(sub)
    rows.append(long_block)

pairs = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
    columns=["EQP_ID", "VAR1", "VAR2", "R", "N"]
)
pairs["ABS_R"] = pairs["R"].abs()
pairs["STRENGTH"] = np.select(
    [pairs["ABS_R"] >= 0.9, pairs["ABS_R"] >= 0.7, pairs["ABS_R"] >= 0.4],
    ["매우강함", "강함", "보통"],
    default="약함",
)
pairs["DIRECTION"] = np.where(pairs["R"] >= 0, "정(+)", "부(-)")
pairs[["R", "ABS_R"]] = pairs[["R", "ABS_R"]].round(4)

strong = pairs[pairs["ABS_R"] >= float(min_abs_r)].sort_values("ABS_R", ascending=False).reset_index(drop=True)
strong["RANK"] = np.arange(1, len(strong) + 1)
strong["DROP_CANDIDATE"] = strong["ABS_R"] >= 0.95

if strong.empty:  # 빈 출력 방지
    strong = pd.DataFrame(
        [{"EQP_ID": "NONE", "VAR1": "NONE", "VAR2": "NONE", "R": 0.0, "N": 0,
          "ABS_R": 0.0, "STRENGTH": "없음", "DIRECTION": "-", "RANK": 0, "DROP_CANDIDATE": False}]
    )

output = pairs
output_pairs = strong
```

## 핵심 포인트

- `df.corr()` 는 **숫자 컬럼만** 자동으로 골라 계산합니다. 문자열 컬럼은 알아서 빠집니다.
  단 `numeric_only` 동작이 버전마다 달랐으니 `select_dtypes(include="number")` 로 명시하는 편이 안전합니다.
- **`np.triu` 로 위쪽 삼각형만** 남기는 것이 핵심입니다. 안 그러면 `(A,B)` 와 `(B,A)` 가 중복되고
  대각선의 `r=1.0` 이 랭킹 1위를 차지합니다.
- `stack()` 은 Wide 매트릭스를 (행, 열, 값) Long 형태로 뒤집습니다. `melt` 와 함께 기억해 두세요.
- **상관은 인과가 아닙니다.** 같은 설비의 두 센서가 0.95라면 대개 "같은 것을 두 번 재고 있는 것"입니다.
  → 모델링 전 **다중공선성 제거 후보**로 쓰기 좋습니다. `DROP_CANDIDATE` 컬럼이 그 역할입니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input(wide 센서 데이터), min_abs_r(float).
TIMESTAMP, EQP_ID 를 제외한 숫자 컬럼들 사이의 피어슨 상관을 EQP_ID 별로 계산해줘.
1. 결과를 (EQP_ID, VAR1, VAR2, R) long 포맷으로. 단 자기 자신과의 상관(대각선)과
   (A,B)/(B,A) 중복은 제거할 것 (상삼각행렬만 사용)
2. |R| >= min_abs_r 인 쌍만 뽑아 |R| 내림차순 랭킹 테이블 생성
   - STRENGTH 컬럼: |R|>=0.9 '매우강함', >=0.7 '강함', >=0.4 '보통', 그 외 '약함'
   - 상관이 매우 높은 쌍(|R|>=0.95)은 DROP_CANDIDATE=True 로 표시 (다중공선성 후보)
3. 표본이 30개 미만인 조합은 계산에서 제외
결과가 비어도 오류가 나지 않도록 방어해줘. 출력: output, output_pairs
```

## 확인 & 응용

- `output` 으로 히트맵(X=VAR1, Y=VAR2, 색=R)을, `output_pairs` 로 랭킹 표를 만들면 한 페이지가 완성됩니다.
- **응용**: `method="spearman"` 으로 바꾸면 비선형 단조 관계도 잡힙니다. 두 결과의 차이가 크면 관계가 비선형입니다.
- **응용**: [14번 예제](../14-merge-asof/)로 센서와 계측값을 붙인 뒤,
  `THICKNESS` 와 가장 상관이 높은 센서를 찾아보세요. 원인 분석의 출발점이 됩니다.

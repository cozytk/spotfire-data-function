---
title: "03. 값 치환과 조건부 파생 컬럼 (그리고 inplace 함정)"
parent: 예제 모음
nav_order: 3
---

# 03. 값 치환과 조건부 파생 컬럼 (그리고 inplace 함정)
{: .no_toc }

**난이도** ★☆☆ · **Level 1 · 정제 기초**

replace / fillna / np.select 로 코드값 정리와 다중 조건 등급 부여를 한 번에. 최신 pandas에서 inplace가 조용히 실패하는 이유도 짚습니다.

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/03_replace_and_derive.py)

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
| 입력 | `cpk_target` | Value | 문서 속성 (예: `1.33`) |
| 출력 | `output` | Table | 새 데이터 테이블 |

---

## 시나리오

- `IS_DEFECT` 컬럼에 `REAL` / `FALSE` 가 섞여 있어 `TRUE` / `FALSE` 로 정리해야 합니다.
- `SIZE_Y` 결측은 최소 측정 단위인 `0.1` 로 채웁니다.
- `THICKNESS` 와 규격을 비교해 **OK / 관찰 / NG** 3등급 판정 컬럼을 새로 만듭니다.
- 판정 기준(규격 중심값·허용폭)은 **분석가가 화면에서 바꿀 수 있어야** 합니다.

## 왜 Spotfire 기본 기능으로는 어려운가

계산 컬럼으로도 `CASE WHEN` 은 가능합니다. 다만,

- 조건이 5개를 넘으면 표현식이 길어지고, 컬럼마다 복사·수정해야 해 유지보수가 어렵습니다.
- **규격 값을 여러 컬럼에서 함께 쓰려면** 문서 속성 + 계산 컬럼을 컬럼 수만큼 만들어야 합니다.
- 데이터 함수는 `SPEC = {...}` 딕셔너리 하나로 공정별 규격을 관리하고, 로직을 한 곳에 모을 수 있습니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 입력 | `cpk_target` | Value (Real) | 문서 속성 `CpkTarget` (기본 1.33) |
| 출력 | `output` | Table | 판정 결과 테이블 |

> `cpk_target` 처럼 **Value 입력을 문서 속성에 연결**하고, 텍스트 영역에 속성 컨트롤(슬라이더/드롭다운)을 놓으면
> 사용자가 값을 바꿀 때마다 데이터 함수를 다시 돌릴 수 있습니다. 자세한 내용은 [20번 예제](../20-parameterize/).

## 스크립트

```python
import numpy as np
import pandas as pd

df = input.copy()

# 1) 코드값 정리 : dict 로 여러 값을 한 번에 치환
df["IS_DEFECT"] = df["IS_DEFECT"].replace({"REAL": "TRUE", "R": "TRUE", "Y": "TRUE"})

# 2) 결측 대치 : inplace 대신 재할당 (또는 df.fillna({...}))
df = df.fillna({"SIZE_Y": 0.1})

# 3) 공정별 규격 마스터 (중심값, 허용 편차율)
SPEC = {
    "PC": (520.0, 0.03),
    "RMG": (310.0, 0.03),
    "CBCMP": (980.0, 0.02),
    "ETCH": (145.0, 0.05),
    "PHOTO": (88.0, 0.05),
}
df["SPEC_CENTER"] = df["STEP_DESC"].map(lambda s: SPEC.get(s, (np.nan, np.nan))[0])
df["SPEC_TOL"] = df["STEP_DESC"].map(lambda s: SPEC.get(s, (np.nan, np.nan))[1])

# 4) 규격 중심 대비 편차율(%)
df["DEV_PCT"] = (df["THICKNESS"] - df["SPEC_CENTER"]) / df["SPEC_CENTER"] * 100

# 5) 다중 조건 판정 : np.select (위에서부터 우선순위)
abs_dev = df["DEV_PCT"].abs() / 100
conditions = [
    df["THICKNESS"].isna(),
    abs_dev > df["SPEC_TOL"],
    abs_dev > df["SPEC_TOL"] * 0.8,
]
choices = ["판정불가", "NG", "관찰"]
df["JUDGE"] = np.select(conditions, choices, default="OK")

# 6) 참고용 : 목표 Cpk 를 만족하려면 허용되는 표준편차 상한
df["SIGMA_MAX_FOR_TARGET"] = (df["SPEC_CENTER"] * df["SPEC_TOL"]) / (3 * cpk_target)

output = df.reset_index(drop=True)
```

## 핵심 포인트

**① `inplace=True` 를 쓰지 마세요.**

교육에서 자주 보이는 아래 코드는 최신 pandas(2.x 후반~3.x)에서 **아무 일도 일어나지 않거나 경고와 함께 무시**됩니다.

```python
df['SIZE_Y'].fillna(0.1, inplace=True)      # X : 원본이 안 바뀔 수 있음 (chained assignment)
```

권장 형태는 둘 중 하나입니다.

```python
df['SIZE_Y'] = df['SIZE_Y'].fillna(0.1)     # O
df = df.fillna({'SIZE_Y': 0.1})             # O : 여러 컬럼을 한 번에
```

**② `replace` 는 dict 로 여러 값을 한 번에.** `df['X'].replace({'REAL': 'TRUE', 'R': 'TRUE'})`

**③ 다중 조건은 `np.select`.** `if/elif` 를 행마다 도는 `apply` 보다 수십 배 빠르고 읽기도 좋습니다.

```python
conditions = [조건1, 조건2, 조건3]
choices    = ["NG", "관찰", "OK"]
df["JUDGE"] = np.select(conditions, choices, default="판정불가")
```
조건은 **위에서부터** 평가되므로 순서가 곧 우선순위입니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input(DataFrame), cpk_target(float).
1) IS_DEFECT 값 'REAL'을 'TRUE'로 치환
2) SIZE_Y 결측은 0.1로 채움
3) STEP_DESC 별 규격이 아래와 같을 때 THICKNESS 로 OK/관찰/NG 판정 컬럼 JUDGE 생성
   PC: 목표 520, 허용 ±3%,  RMG: 310 ±3%,  CBCMP: 980 ±2%,  ETCH: 145 ±5%,  PHOTO: 88 ±5%
   - 규격 밖이면 NG, 허용폭의 80% 초과면 '관찰', 나머지 OK
4) 규격 중심 대비 편차율(%) 컬럼 DEV_PCT 도 추가
조건문은 np.select 로 벡터화해서 작성하고 apply(axis=1) 은 쓰지 마.
inplace=True 금지. 결과는 output 에 할당.
```

## 확인 & 응용

- `JUDGE` 별 건수를 세어 NG가 특정 설비(`EQP_ID`)에 몰려 있는지 확인하세요.
- **응용**: `SPEC` 딕셔너리를 **별도 입력 테이블**(규격 마스터)로 바꾸고 `merge` 로 붙이면
  코드 수정 없이 규격을 관리할 수 있습니다. 실무에서는 이 방식을 권장합니다.

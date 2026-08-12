---
title: 24. 공개 데이터셋 종합 실습 (titanic / iris / diabetes)
parent: 예제 모음
nav_order: 24
---

# 24. 공개 데이터셋 종합 실습 (titanic / iris / diabetes)
{: .no_toc }

**난이도** ★★☆ · **Level 4 · 통계·자동화·Spotfire 고유 기능**

사내 데이터 없이도 연습할 수 있도록, 잘 알려진 3개 데이터셋으로 전처리·파생·요약의 전 과정을 한 번에 훑습니다.

사용 데이터: [`titanic.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/titanic.csv), [`iris.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/iris.csv), [`diabetes_train.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/diabetes_train.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/24_public_datasets.py)

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

### 파라미터 요약
{: .no_toc }

| 구분 | 이름 | 타입 | 연결 |
|---|---|---|---|
| 입력 | `input_titanic` | Table | `titanic.csv` |
| 입력 | `input_iris` | Table | `iris.csv` |
| 입력 | `input_diabetes` | Table | `diabetes_train.csv` |
| 출력 | `output_titanic` | Table | 새 데이터 테이블 |
| 출력 | `output_iris` | Table | 새 데이터 테이블 |
| 출력 | `output_diabetes` | Table | 새 데이터 테이블 |

---

## 시나리오

교육장에서는 사내 데이터를 쓸 수 없는 경우가 많습니다. 이 예제는 공개 데이터 3종으로
**실무에서 반복되는 전처리 패턴**을 모두 담았습니다.

| 데이터 | 연습하는 기술 | 실무 대응 |
|---|---|---|
| `titanic.csv` | 결측 대치, 정규식 파생, 구간화, 원-핫 인코딩 | 마스터 데이터 정제 |
| `iris.csv` | 그룹 통계, 판별 규칙 도출 | 품종/등급 분류 규칙 |
| `diabetes_train.csv` | **"0으로 위장한 결측"** 처리, 위험도 등급 | 센서 미취득값 처리 |

## 이 예제의 진짜 교훈: `diabetes_train.csv` 의 0

`Glucose`(혈당), `BloodPressure`(혈압), `BMI` 가 **0** 인 행이 있습니다.
살아 있는 사람의 혈당이 0일 수는 없습니다. 즉 **0은 결측을 의미**합니다.

이걸 모르고 평균을 내면 **혈당 평균이 실제보다 낮게** 나옵니다.
반도체 데이터에서 "센서 미취득이 0으로 기록되는" 상황과 **정확히 같은 문제**입니다.

> **데이터를 받으면 가장 먼저 물어야 할 질문: "이 컬럼에서 0은 진짜 0인가, 결측인가?"**

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input_titanic` / `input_iris` / `input_diabetes` | Table | 각 데이터 테이블 |
| 출력 | `output_titanic` / `output_iris` / `output_diabetes` | Table | 각 처리 결과 |

## 스크립트

```python
import numpy as np
import pandas as pd

# =====================================================================
# 1) TITANIC : 결측 대치 + 정규식 파생 + 구간화 + 원-핫 인코딩
# =====================================================================
tt = input_titanic.copy()

# 이름에서 호칭 추출 (" Mr." 형태) — 텍스트에서 정보를 뽑는 대표 패턴
tt["TITLE"] = tt["Name"].str.extract(r" ([A-Za-z]+)\.", expand=False)
rare = tt["TITLE"].value_counts()
tt["TITLE"] = tt["TITLE"].where(tt["TITLE"].isin(rare[rare >= 10].index), "Rare")

# 나이 결측 : 전체 평균이 아니라 '호칭별 중앙값'으로 대치해야 정확하다
tt["AGE_IMPUTED"] = tt["Age"].isna()
tt["Age"] = tt["Age"].fillna(tt.groupby("TITLE")["Age"].transform("median"))
tt["Age"] = tt["Age"].fillna(tt["Age"].median())

tt["Embarked"] = tt["Embarked"].fillna(tt["Embarked"].mode().iloc[0])
tt["CABIN_DECK"] = tt["Cabin"].astype(str).str[0].where(tt["Cabin"].notna(), "Unknown")

# 파생 변수
tt["FAMILY_SIZE"] = tt["SibSp"] + tt["Parch"] + 1
tt["IS_ALONE"] = tt["FAMILY_SIZE"] == 1

# 구간화 : pd.cut(값 기준) vs pd.qcut(분위수 기준)
tt["AGE_GROUP"] = pd.cut(
    tt["Age"], bins=[0, 12, 19, 39, 59, 200],
    labels=["아동", "청소년", "청년", "중년", "노년"],
)
tt["FARE_QUARTILE"] = pd.qcut(tt["Fare"], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")

# 원-핫 인코딩
dummies = pd.get_dummies(tt[["Sex", "Embarked"]], prefix=["SEX", "EMB"], drop_first=False)
tt = pd.concat([tt, dummies], axis=1)
tt["AGE_GROUP"] = tt["AGE_GROUP"].astype(str)     # 범주형은 문자열로 변환해 내보낸다
tt["FARE_QUARTILE"] = tt["FARE_QUARTILE"].astype(str)

output_titanic = tt

# =====================================================================
# 2) IRIS : 그룹 요약 + 데이터에서 판별 규칙 도출
# =====================================================================
ir = input_iris.copy()
measure_cols = ["sepal_length", "sepal_width", "petal_length", "petal_width"]

iris_summary = (
    ir.melt(id_vars="species", value_vars=measure_cols, var_name="MEASURE", value_name="VALUE")
    .groupby(["species", "MEASURE"], as_index=False)
    .agg(N=("VALUE", "size"), MEAN=("VALUE", "mean"), STD=("VALUE", "std"),
         MIN=("VALUE", "min"), MAX=("VALUE", "max"))
)
iris_summary[["MEAN", "STD"]] = iris_summary[["MEAN", "STD"]].round(3)

# petal_length 로 품종을 나누는 임계값을 '데이터에서' 찾는다
order = ir.groupby("species")["petal_length"].mean().sort_values().index.tolist()
cut1 = (ir.loc[ir["species"] == order[0], "petal_length"].max()
        + ir.loc[ir["species"] == order[1], "petal_length"].min()) / 2
cut2 = (ir.loc[ir["species"] == order[1], "petal_length"].quantile(0.75)
        + ir.loc[ir["species"] == order[2], "petal_length"].quantile(0.25)) / 2

pred = np.select([ir["petal_length"] <= cut1, ir["petal_length"] <= cut2],
                 [order[0], order[1]], default=order[2])
accuracy = float((pred == ir["species"]).mean())

iris_summary["RULE"] = f"petal_length <= {cut1:.2f} -> {order[0]}, <= {cut2:.2f} -> {order[1]}, else {order[2]}"
iris_summary["RULE_ACCURACY"] = round(accuracy, 4)

output_iris = iris_summary

# =====================================================================
# 3) DIABETES : '0으로 위장한 결측' 처리
# =====================================================================
db = input_diabetes.copy()
ZERO_IS_MISSING = ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"]

# 0을 방치했을 때와 결측 처리했을 때의 평균 차이를 나란히 기록
compare = []
for col in ZERO_IS_MISSING:
    with_zero = float(db[col].mean())
    without_zero = float(db.loc[db[col] != 0, col].mean())
    compare.append(
        {
            "COLUMN": col,
            "ZERO_CNT": int((db[col] == 0).sum()),
            "ZERO_PCT": round(float((db[col] == 0).mean() * 100), 2),
            "MEAN_WITH_ZERO": round(with_zero, 3),
            "MEAN_WITHOUT_ZERO": round(without_zero, 3),
            "DISTORTION_PCT": round((with_zero - without_zero) / without_zero * 100, 2),
        }
    )

# 0 -> NaN 변환 후 Outcome 그룹별 중앙값으로 대치
db[ZERO_IS_MISSING] = db[ZERO_IS_MISSING].replace(0, np.nan)
for col in ZERO_IS_MISSING:
    db[col] = db[col].fillna(db.groupby("Outcome")[col].transform("median"))
    db[col] = db[col].fillna(db[col].median())

# 위험도 점수 (0~4) 와 등급
db["RISK_SCORE"] = (
    (db["Glucose"] >= 140).astype(int)
    + (db["BMI"] >= 30).astype(int)
    + (db["Age"] >= 45).astype(int)
    + (db["BloodPressure"] >= 90).astype(int)
)
db["RISK_LEVEL"] = np.select(
    [db["RISK_SCORE"] >= 3, db["RISK_SCORE"] == 2, db["RISK_SCORE"] == 1],
    ["고위험", "중위험", "저위험"],
    default="정상",
)

distortion = pd.DataFrame(compare)
risk_summary = (
    db.groupby("RISK_LEVEL", as_index=False)
    .agg(N=("Outcome", "size"), POSITIVE=("Outcome", "sum"))
)
risk_summary["POSITIVE_RATE_PCT"] = (risk_summary["POSITIVE"] / risk_summary["N"] * 100).round(2)

# 두 요약을 한 테이블로 합쳐 내보낸다 (출력 개수를 늘려도 무방)
distortion["SECTION"] = "0값 왜곡 비교"
risk_summary["SECTION"] = "위험도 등급별 유병률"
output_diabetes = pd.concat([distortion, risk_summary], ignore_index=True).fillna(
    {"COLUMN": "-", "RISK_LEVEL": "-"}
)
```

## 핵심 포인트

- **`str.extract(r" ([A-Za-z]+)\.")`** — Titanic 이름에서 `Mr`, `Mrs`, `Master` 같은 호칭을 뽑아냅니다.
  호칭은 성별·연령·사회적 지위 정보를 압축한 강력한 파생 변수입니다.
  **텍스트에서 정보를 뽑는 것**은 [16번 예제](../16-regex-parse-log/)와 완전히 같은 기술입니다.
- **`pd.cut`** = 값 기준 구간화(연령대), **`pd.qcut`** = 분위수 기준 구간화(요금 4분위).
  둘의 차이를 아는 것이 구간화의 전부입니다.
- **`pd.get_dummies`** 로 범주형을 0/1 컬럼으로 펼칩니다. 모델링 입력을 만들 때 필수입니다.
  단 컬럼이 폭증하므로 `drop_first=True` 를 고려하세요.
- **호칭별 중앙값으로 나이 대치**는 전체 평균 대치보다 훨씬 정확합니다.
  → 우리 데이터에서는 **"설비/공정별 중앙값 대치"** 가 같은 아이디어입니다 ([08번 예제](../08-impute-smart/)).
- `describe()` 로 요약하고 `T`(전치)로 뒤집는 패턴은 **어떤 데이터를 받든 첫 30초에 하는 작업**입니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 3개: input_titanic, input_iris, input_diabetes.

[titanic]
- Name 에서 호칭(Mr, Mrs, Miss, Master 등)을 정규식으로 추출해 TITLE 컬럼 생성.
  희귀 호칭(빈도 10 미만)은 'Rare' 로 통합
- Age 결측은 TITLE 별 중앙값으로 대치하고 AGE_IMPUTED 플래그 남기기
- Embarked 결측은 최빈값, Cabin 은 첫 글자만 남기고 결측은 'Unknown'
- FAMILY_SIZE = SibSp + Parch + 1, IS_ALONE 파생
- 연령대 구간화(0-12,13-19,20-39,40-59,60+)와 Fare 4분위 등급
- Sex, Embarked 를 원-핫 인코딩
결과: output_titanic

[iris]
- 품종별 각 측정치 평균/표준편차 요약 (long 포맷)
- petal_length 기준으로 품종을 구분하는 단순 임계값 규칙을 데이터에서 도출하고
  그 규칙의 정확도도 계산해서 포함
결과: output_iris

[diabetes]
- Glucose, BloodPressure, SkinThickness, Insulin, BMI 의 0 은 결측을 의미하므로 NaN 으로 변환
- 변환 전후 평균을 비교한 컬럼 포함 (0을 방치하면 얼마나 왜곡되는지 보여주기)
- 결측은 Outcome 그룹별 중앙값으로 대치
- Glucose 와 BMI 로 위험도 점수(0~4)를 만들고 등급('저위험'~'고위험') 부여
결과: output_diabetes
```

## 확인 & 응용

- Titanic: `TITLE` × `Pclass` 별 생존율 크로스탭을 만들어 보세요 ([06번 예제](../06-pivot-crosstab/) 응용).
- Diabetes: `output_diabetes` 의 `MEAN_WITH_ZERO` 와 `MEAN_WITHOUT_ZERO` 차이를 보세요.
  **0을 방치했을 때의 왜곡 크기**가 숫자로 나옵니다. 이 표 하나가 교육 효과가 가장 큽니다.
- Iris: 도출된 임계값 규칙의 정확도가 90%를 넘는지 확인해 보세요.

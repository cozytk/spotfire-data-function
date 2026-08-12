---
title: 5. pandas 속성 코스
parent: 문법
nav_order: 5
---

# 5. pandas 속성 코스
{: .no_toc }

데이터 함수의 본체는 결국 **평범한 pandas 코드**입니다.
여기서는 이 교안의 24개 예제에서 **실제로 쓰인 문법만** 모았습니다.
{: .fs-5 .fw-300 }

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## 0. 데이터를 받으면 가장 먼저 하는 것

```python
df.shape            # (행 수, 열 수)
df.dtypes           # 컬럼별 타입
df.head(10)         # 앞부분 훑어보기
df.isna().sum()     # 컬럼별 결측 개수
df.describe().T     # 숫자 컬럼 요약 통계 (전치해서 보면 편함)
df["EQP_ID"].value_counts()   # 범주별 개수
df["EQP_ID"].nunique()        # 고유값 개수
```

{: .팁 }
> 이 6줄의 결과를 **그대로 AI에게 붙여 주면** 프롬프트 품질이 급격히 올라갑니다.
> 자세한 방법은 [AI 활용법](../../prompting/)에서 다룹니다.

## 1. 선택 — 행과 열 고르기

```python
df["THICKNESS"]                       # 컬럼 하나 (Series)
df[["LOT_ID", "THICKNESS"]]           # 컬럼 여러 개 (DataFrame)

df[df["THICKNESS"] > 500]                                  # 조건 필터
df[(df["THICKNESS"] > 500) & (df["EQP_ID"] == "PC01")]     # AND 는 & (and 아님!)
df[(df["STEP_DESC"] == "PC") | (df["STEP_DESC"] == "RMG")] # OR 는 |
df[df["STEP_DESC"].isin(["PC", "RMG"])]                    # 여러 값 중 하나
df[~df["STEP_DESC"].isin(["PC", "RMG"])]                   # 부정은 ~
df[df["EQP_ID"].str.startswith("ETC")]                     # 문자열 조건
df[df["THICKNESS"].between(500, 540)]                      # 범위
```

{: .주의 }
> **조건마다 괄호가 필요합니다.** `df[df["A"] > 1 & df["B"] < 2]` 는 우선순위 때문에 오작동합니다.
> 반드시 `df[(df["A"] > 1) & (df["B"] < 2)]`.
> 그리고 파이썬의 `and` / `or` 가 **아니라** `&` / `|` 입니다.

## 2. 정렬 · 중복 · 결측

```python
df.sort_values("MEAS_TIME")                              # 오름차순
df.sort_values(["EQP_ID", "MEAS_TIME"], ascending=[True, False])

df.drop_duplicates()                                     # 완전 중복 제거
df.drop_duplicates(subset=["LOT_ID", "WAFER_NO"], keep="last")   # 키 기준
df.duplicated(subset=["LOT_ID"]).sum()                   # 중복 개수 확인

df.dropna()                                              # 한 컬럼이라도 비면 삭제 (주의!)
df.dropna(subset=["THICKNESS", "CD"])                    # 대상 컬럼 지정 (권장)
df.fillna({"SIZE_Y": 0.1, "CHAMBER": "UNKNOWN"})         # 컬럼별 대치
df["X"].ffill()                                          # 직전 값으로 채움
```

## 3. 컬럼 만들기

```python
df["DEV"] = df["THICKNESS"] - 520                        # 산술 연산 (벡터 연산)
df["RATIO"] = df["GOOD_DIE"] / df["TOTAL_DIE"]

# 조건 2개 이하 -> np.where
df["JUDGE"] = np.where(df["THICKNESS"] > 540, "NG", "OK")

# 조건 3개 이상 -> np.select (위에서부터 우선순위)
df["GRADE"] = np.select(
    [df["Z"].abs() > 3, df["Z"].abs() > 2],
    ["심각", "주의"],
    default="정상",
)

# 값 치환
df["IS_DEFECT"] = df["IS_DEFECT"].replace({"REAL": "TRUE"})
df["STEP_KOR"] = df["STEP_DESC"].map({"PC": "세정", "ETCH": "식각"})

# 구간화
df["AGE_GRP"] = pd.cut(df["Age"], bins=[0, 20, 40, 60, 200], labels=["20이하","20대30대","40대50대","60이상"])
df["QUARTILE"] = pd.qcut(df["Fare"], 4, labels=["Q1","Q2","Q3","Q4"])
```

{: .주의 }
> **`apply(axis=1)` 은 되도록 쓰지 마세요.** 행마다 파이썬 함수를 호출해서 수십 배 느립니다.
> 위의 `np.where` / `np.select` 로 거의 모든 조건 로직을 표현할 수 있습니다.

## 4. 그룹 집계 — `agg` vs `transform`

**이 둘의 차이가 pandas에서 가장 중요한 개념입니다.**

| | 결과 행 수 | 용도 |
|---|---|---|
| `groupby().agg()` | **그룹 수**만큼 | 요약 테이블 만들기 |
| `groupby().transform()` | **원본과 동일** | 원본에 통계를 되붙이기 |

```python
# agg : 요약 테이블 (행이 줄어듦)
summary = df.groupby("EQP_ID", as_index=False).agg(
    N=("THICKNESS", "size"),
    MEAN=("THICKNESS", "mean"),
    STD=("THICKNESS", "std"),
    LOTS=("LOT_ID", "nunique"),
)

# transform : 원본 행 수 유지 (되붙이기)
df["GRP_MEAN"] = df.groupby("EQP_ID")["THICKNESS"].transform("mean")
df["Z"] = (df["THICKNESS"] - df["GRP_MEAN"]) / df.groupby("EQP_ID")["THICKNESS"].transform("std")
```

`as_index=False` 를 쓰면 그룹 키가 **인덱스가 아니라 컬럼**으로 남아 Spotfire로 내보내기 편합니다.

자주 쓰는 집계 함수: `size`, `count`, `sum`, `mean`, `median`, `std`, `min`, `max`, `nunique`, `first`, `last`

## 5. 테이블 합치기

```python
# 가로로 붙이기 (조인)
merged = left.merge(right, on="LOT_ID", how="left")          # how: left/inner/outer/right
merged = left.merge(right, on="LOT_ID", how="left", indicator=True)   # 매칭 여부 확인

# 세로로 쌓기
stacked = pd.concat([df1, df2], ignore_index=True)

# 시간 근접 조인 (정확히 안 맞는 시각끼리)
pd.merge_asof(left, right, on="TIME", by="EQP_ID",
              direction="backward", tolerance=pd.Timedelta("30min"))
```

## 6. 구조 바꾸기 — melt / pivot

```python
# Wide -> Long : 컬럼이 많을 때
long_df = df.melt(id_vars=["TIMESTAMP", "EQP_ID"], var_name="SENSOR", value_name="VALUE")

# Long -> Wide : 크로스탭
pv = df.pivot_table(index="EQP_ID", columns="STEP_DESC", values="THICKNESS",
                    aggfunc="mean", margins=True, margins_name="합계")

# 내보내기 전 필수 정리
pv = pv.reset_index()
pv.columns = [str(c) for c in pv.columns]
```

## 7. 시계열

```python
df["T"] = pd.to_datetime(df["MEAS_TIME"])
df = df.sort_values("T")                                  # 시계열 연산 전에 반드시 정렬!

# 이동 통계
df["MA"] = df["X"].rolling(25, min_periods=5).mean()
df["MSTD"] = df["X"].rolling(25, min_periods=5).std()
df["EWMA"] = df["X"].ewm(span=25, adjust=False).mean()

# 그룹별 이동 통계
df["MA"] = df.groupby("EQP_ID")["X"].transform(lambda s: s.rolling(25, min_periods=5).mean())

# 이전/다음 값, 변화량
df["PREV"] = df.groupby("EQP_ID")["X"].shift()
df["DIFF"] = df.groupby("EQP_ID")["X"].diff()

# 시간 단위 재집계 (빈 구간도 생성됨)
hourly = df.set_index("T").resample("1h").agg(N=("X", "size"), MEAN=("X", "mean"))
```

## 8. 문자열

```python
df["EQP_ID"].str.strip().str.upper()             # 공백 제거, 대문자
df["MESSAGE"].str.contains("pressure", case=False, na=False)
df["MESSAGE"].str.extract(r"\[(?P<CODE>[A-Z]-\d+)\]")     # 정규식으로 컬럼 추출
df["CABIN"].str[0]                               # 첫 글자
df["LOT_ID"] + "-" + df["WAFER_NO"].astype(str)  # 문자열 결합
df["A"].str.split("_", expand=True)              # 분리해서 여러 컬럼으로
```

## 9. 꼭 기억할 관용구 3개

**① 누적 그룹 번호 (연속 구간 묶기)**

```python
new_group = df.groupby("EQP_ID")["TIME"].diff() > pd.Timedelta("30min")
df["SESSION"] = new_group.groupby(df["EQP_ID"]).cumsum()
```

**② 값이 바뀌는 지점 찾기**

```python
df["CHANGED"] = df["STATE"] != df["STATE"].shift()
df["BLOCK_ID"] = df["CHANGED"].cumsum()
```

**③ 파레토 (누적 비율)**

```python
s = df.sort_values("AMOUNT", ascending=False)
s["CUM_PCT"] = s["AMOUNT"].cumsum() / s["AMOUNT"].sum()
```

## 10. 데이터 함수 마무리 습관

```python
result = result.reset_index(drop=True)                 # 인덱스 정리
result.columns = [str(c) for c in result.columns]      # 컬럼명 문자열화
if len(result) == 0:                                   # 빈 결과 방어
    result = pd.DataFrame([{"NOTE": "조건에 맞는 데이터가 없습니다"}])
output = result                                        # 출력 변수에 할당
```

---

## 정리

외워야 할 것은 사실상 이것뿐입니다.

1. 조건 필터는 `&`, `|`, `~` 와 **괄호**
2. `agg` 는 줄이고, `transform` 은 되붙인다
3. 조건 분기는 `np.select`, `apply(axis=1)` 은 피한다
4. 시계열 연산 전에는 **정렬**
5. 내보내기 전에는 **인덱스 해제 + 컬럼명 문자열화 + 빈 결과 방어**

다음: [등록·디버깅·성능](../06-run-debug/)

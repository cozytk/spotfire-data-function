---
title: 치트시트
parent: 참고 자료
nav_order: 2
---

# 치트시트
{: .no_toc }

한 장으로 보는 요약. 실습 중 옆에 띄워 두세요.
{: .fs-5 .fw-300 }

---

## 데이터 함수 기본 틀

```python
import pandas as pd
import numpy as np

df = input.copy()          # 입력 (파라미터 이름과 일치해야 함)

# ... 처리 ...

output = df.reset_index(drop=True)    # 출력 (반드시 할당)
```

## 파라미터

| 타입 | Python | 연결 대상 |
|---|---|---|
| Value | `str/int/float/bool` | 문서 속성, 표현식 |
| Column | `Series` | 컬럼 |
| Table | `DataFrame` | 데이터 테이블 |

**입력 제한**: 없음 / 필터링 / **마킹** / 둘 다(교집합)

## 타입 매핑

| Spotfire | pandas |
|---|---|
| Integer / LongInteger | `int32` / `int64` |
| Real / SingleReal | `float64` / `float32` |
| String | `object` |
| Boolean | `bool` |
| Date / DateTime | `datetime64[ns]` |
| TimeSpan | `timedelta64[ns]` |
| Binary | `bytes` |

## 탐색

```python
df.shape            df.dtypes           df.head(10)
df.isna().sum()     df.describe().T     df["A"].value_counts()
```

## 선택·필터

```python
df[["A", "B"]]
df[df["A"] > 10]
df[(df["A"] > 10) & (df["B"] == "PC")]      # and 아니라 &, 괄호 필수
df[df["A"].isin(["X", "Y"])]                # ~ 는 부정
df[df["A"].str.startswith("ETC")]
df.query("A > 10 and B == 'PC'")
```

## 정제

```python
df.drop_duplicates()
df.drop_duplicates(subset=["K"], keep="last")
df.dropna(subset=["A", "B"])                # subset 없으면 한 컬럼만 비어도 삭제!
df.fillna({"A": 0, "B": "UNKNOWN"})
df["A"] = df["A"].fillna(df["A"].median())  # inplace 대신 재할당
df["A"].replace({"REAL": "TRUE"})
df.columns = df.columns.str.strip()
```

## 파생 컬럼

```python
df["C"] = df["A"] - df["B"]
df["F"] = np.where(조건, "Y", "N")                       # 조건 2개
df["G"] = np.select([조건1, 조건2], ["A", "B"], "기타")   # 조건 3개 이상
df["H"] = pd.cut(df["A"], bins=[0,10,20], labels=["소","대"])
df["I"] = pd.qcut(df["A"], 4, labels=["Q1","Q2","Q3","Q4"])
df["J"] = df["A"].map({"PC": "세정"})
```

## 그룹

```python
# agg : 행이 줄어듦 (요약)
df.groupby("G", as_index=False).agg(N=("A","size"), MEAN=("A","mean"))

# transform : 행 수 유지 (되붙이기)
df["GM"] = df.groupby("G")["A"].transform("mean")
df["Z"] = (df["A"] - df.groupby("G")["A"].transform("mean")) \
          / df.groupby("G")["A"].transform("std")
```

집계 함수: `size count sum mean median std min max nunique first last`

## 합치기

```python
left.merge(right, on="K", how="left", indicator=True)
pd.concat([df1, df2], ignore_index=True)
pd.merge_asof(l, r, on="T", by="EQP", direction="backward",
              tolerance=pd.Timedelta("30min"))          # 양쪽 정렬 필수
```

## 구조 변환

```python
df.melt(id_vars=["T","EQP"], var_name="NAME", value_name="VALUE")
df.pivot_table(index="A", columns="B", values="C", aggfunc="mean", margins=True)

pv = pv.reset_index()                          # 내보내기 전 필수
pv.columns = [str(c) for c in pv.columns]
```

## 시계열

```python
df["T"] = pd.to_datetime(df["T"])
df = df.sort_values(["G", "T"])                # 반드시 먼저!

df.groupby("G")["A"].shift()                   # 이전 값
df.groupby("G")["A"].diff()                    # 변화량
df.groupby("G")["A"].transform(lambda s: s.rolling(25, min_periods=5).mean())
df["A"].ewm(span=25, adjust=False).mean()
df.set_index("T").resample("1h").agg(N=("A","size"))
```

빈도 문자열: `15min` `1h` `1D` `1W` `1MS`

## 문자열·정규식

```python
df["A"].str.strip().str.upper()
df["A"].str.contains("키워드", case=False, na=False)
df["A"].str.extract(r"\[(?P<CODE>[A-Z]-\d+)\]")
pd.to_numeric(df["A"], errors="coerce")
```

| 패턴 | 의미 |
|---|---|
| `\d+` | 숫자 1개 이상 |
| `[\d.]+` | 숫자와 소수점 |
| `\w+` | 영문/숫자/밑줄 |
| `.*?` | 최소 매칭 |
| `(?P<이름>...)` | 이름 있는 캡처 그룹 |

## 필수 관용구 3개

```python
# 연속 구간 세션화
new = df.groupby("K")["T"].diff() > pd.Timedelta("30min")
df["SESSION"] = new.groupby(df["K"]).cumsum()

# 값이 바뀌는 지점
df["BLOCK"] = (df["S"] != df["S"].shift()).cumsum()

# 파레토
s = df.sort_values("V", ascending=False)
s["CUM_PCT"] = s["V"].cumsum() / s["V"].sum()
```

## 마무리 (출력 전)

```python
result = result.reset_index(drop=True)
result.columns = [str(c) for c in result.columns]
if len(result) == 0:
    result = pd.DataFrame([{"NOTE": "데이터 없음"}])
output = result
```

---

## 오류 빠른 참조

| 오류/증상 | 원인 | 해결 |
|---|---|---|
| `NameError: input` | 파라미터 이름 불일치 | 등록된 이름 확인 |
| 출력 변수 없음 | 할당 누락 | 모든 분기에서 할당 |
| `KeyError` | 컬럼명 오타/공백 | `df.columns.str.strip()` |
| 빈 결과 오류 | 전부 결측인 컬럼 | 기본값 1행 반환 |
| `inplace` 무효 | 연쇄 할당 | 재할당 형태로 |
| `SettingWithCopyWarning` | 필터 결과에 대입 | `.copy()` 추가 |
| 조인 후 행 폭증 | 오른쪽 키 중복 | `drop_duplicates(subset=키)` |
| 조인 후 전부 결측 | 키 공백/대소문자 | `.str.strip().str.upper()` |
| 값이 엉뚱한 행에 | 인덱스 불일치 | `reset_index(drop=True)` |
| 매우 느림 | `apply(axis=1)` | `np.select` / 벡터 연산 |

## 프롬프트 최소 형태

```text
Spotfire Python 데이터 함수. 입력 input(DataFrame), 출력 output.
파일 입출력·print 금지, import 는 스크립트 안에.
컬럼: (컬럼명과 타입)
요구사항:
1. ...
2. ...
제약: inplace 금지, apply(axis=1) 금지, 0으로 나누기·빈 결과 방어.
한국어 주석과 3줄 설명을 붙여줘.
```

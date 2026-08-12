---
title: 기존 실습 스크립트 개선
parent: 참고 자료
nav_order: 4
---

# 기존 실습 스크립트 개선
{: .no_toc }

지금까지 교육에서 쓰던 실습 스크립트를 그대로 두고,
**무엇이 좋고 무엇을 고쳐야 하는지** 하나씩 짚습니다.
{: .fs-5 .fw-300 }

기존 스크립트는 **학습용으로 아주 잘 설계되어 있습니다.** 짧고, 한 줄에 하나의 개념만 담고 있어
처음 배우는 사람에게 적합합니다. 다만 실무에 그대로 쓰면 문제가 되는 지점이 몇 군데 있어
여기서 정리합니다.

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## 1. 특정 컬럼 결측 행 삭제

```python
# 기존
import pandas as pd
df = input
df = df.dropna(subset=['Age'])
output = df
```

**평가: 좋습니다.** `subset` 을 명시한 것이 정확한 습관입니다.

보완한다면 **몇 건이 지워졌는지 남기는 것**입니다.

```python
import pandas as pd

df = input.copy()
n_before = len(df)
df = df.dropna(subset=["Age"])

output = df.reset_index(drop=True)
output_report = pd.DataFrame([{
    "STEP": "Age 결측 제거",
    "BEFORE": n_before,
    "REMOVED": n_before - len(df),
    "AFTER": len(df),
}])
```

→ [02번 예제](../../examples/02-missing-and-zero/)

---

## 2. 전체 결측 행 삭제

```python
# 기존
df = df.dropna()
```

**주의가 필요합니다.** `dropna()` 의 기본값은 `how="any"` 로,
**한 컬럼이라도 비어 있으면 그 행을 삭제**합니다.

컬럼이 15개인 `fab_measurement` 에서 이 코드를 실행하면 데이터가 크게 줄어듭니다.
"결측 있는 행을 지웠다"고 보고했는데 **실제로는 데이터의 30%가 사라진** 상황이 생깁니다.

```python
df = df.dropna(subset=["THICKNESS", "CD"])       # ✅ 분석에 꼭 필요한 컬럼만
df = df.dropna(thresh=len(df.columns) - 2)       # 또는: 결측이 3개 이상인 행만 삭제
```

{: .팁 }
> 실행 전후로 `len(df)` 를 반드시 비교하세요. 이 한 가지 습관이 많은 사고를 막습니다.

---

## 3. 0이 있는 행 삭제

```python
# 기존
df = df[(df != 0).all(axis=1)]
```

**이 코드가 가장 위험합니다.** 모든 컬럼을 검사하기 때문에

- `PARTICLE_CNT = 0` (파티클 없음 = **양품**) → 삭제됨
- `WAFER_NO` 가 0부터 시작하는 시스템 → 첫 웨이퍼 전부 삭제
- 각종 플래그 컬럼의 `0`(=False) → 삭제됨

즉 **정상 데이터를 대량으로 지우면서 오류는 나지 않습니다.**

```python
# ✅ 0이 '결측'을 의미하는 컬럼만 명시적으로 지정
ZERO_IS_MISSING = ["PRESSURE", "TEMP"]
df = df[~(df[ZERO_IS_MISSING] == 0).any(axis=1)]
```

이것이 이 교안에서 반복해서 강조하는 질문입니다.

> **"이 컬럼에서 0은 진짜 0인가, 결측인가?"**

→ [02번 예제](../../examples/02-missing-and-zero/), [24번 예제](../../examples/24-public-datasets/)

---

## 4. 중복 행 삭제

```python
# 기존
df = df.drop_duplicates()
```

**평가: 좋습니다.** 그리고 이것은 **Spotfire에 공식적인 대응 기능이 없는** 대표 사례라
데이터 함수의 가치를 보여 주기에 가장 좋은 첫 예제입니다.

실무에서 한 걸음 더 나아가면, **"완전히 같은 행"보다 "같은 대상의 재측정"** 이 더 흔한 문제입니다.

```python
# 같은 (LOT, WAFER, STEP) 중 가장 최근 측정만 남기기
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])
df = df.sort_values(["LOT_ID", "WAFER_NO", "STEP_DESC", "MEAS_TIME"])
df = df.drop_duplicates(subset=["LOT_ID", "WAFER_NO", "STEP_DESC"], keep="last")
```

→ [01번 예제](../../examples/01-dedup-latest/)

---

## 5. 조인 + 값 정리 (기능 3개 합치기)

```python
# 기존
df1 = input1
df2 = input2
df = pd.merge(df1, df2, on='JOIN_ID')
df['IS_DEFECT'] = df['IS_DEFECT'].replace('REAL', "TRUE")
df['SIZE_Y'].fillna(0.1, inplace=True)
output = df
```

**개념 전달용으로는 훌륭합니다.** 고칠 점 세 가지가 있습니다.

### ① `inplace=True` 는 동작하지 않을 수 있다

```python
df['SIZE_Y'].fillna(0.1, inplace=True)   # ❌ 최신 pandas 에서 원본이 안 바뀜
df["SIZE_Y"] = df["SIZE_Y"].fillna(0.1)  # ✅
```

이것은 pandas 버전에 따라 **경고만 뜨고 조용히 무시**됩니다.
Spotfire 버전을 올린 뒤 "예전엔 됐는데 지금은 안 된다"는 문의의 대표 원인입니다.

### ② `merge` 의 기본값은 `inner`

`how` 를 지정하지 않으면 **양쪽에 다 있는 행만** 남습니다.
계측 데이터에 LOT 마스터를 붙이는 상황이라면, 마스터에 없는 LOT은 **조용히 사라집니다.**

```python
df = pd.merge(df1, df2, on="JOIN_ID", how="left", indicator=True)
print(df["_merge"].value_counts())     # both / left_only 확인
```

### ③ 조인 키 정규화가 없다

```python
for d in (df1, df2):
    d["JOIN_ID"] = d["JOIN_ID"].astype(str).str.strip().str.upper()
```

→ [04번 예제](../../examples/04-join-and-split/)

---

## 6. 조건별로 3개 테이블로 분리

```python
# 기존
df1 = df[df['Step_desc'] == "PC"]
df2 = df[df['Step_desc'] == "RMG"]
df3 = df[df['Step_desc'] == "CBCMP"]
output1, output2, output3 = df1, df2, df3
```

**평가: 아주 좋은 예제입니다.** "출력을 여러 개 만들 수 있다"는 데이터 함수의 강점을 잘 보여 줍니다.

실무 관점의 보완 두 가지:

### ① 누락되는 행이 생긴다

`PC`, `RMG`, `CBCMP` 외의 값(`ETCH`, `PHOTO`)은 **어느 출력에도 들어가지 않고 사라집니다.**
마지막은 "그 외 전부"로 받는 것이 안전합니다.

```python
df3 = df[~df["STEP_DESC"].isin(["PC", "RMG"])]     # 나머지 전부
```

### ② 빈 결과 방어

조건에 맞는 행이 하나도 없으면 빈 테이블이 되어 Spotfire에서 오류가 날 수 있습니다.
([04번 예제](../../examples/04-join-and-split/)의 `safe()` 함수)

---

## 7. 대출 데이터 실습

```python
# 기존
df['대출기간'] = df['대출기간'].replace({'36 months': '36개월', '60 months': '60개월'})
df['총상환금액'] = df['총상환원금'] + df['총상환이자']
df1 = df[df['대출등급'] == 'A']
...
```

**평가: 좋습니다.** dict 형태의 `replace` 와 컬럼 간 연산을 잘 보여 줍니다.

한 가지만 덧붙이면, **숫자 컬럼이 문자열로 들어오는 경우**가 실무에서 매우 흔합니다.
(쉼표가 포함된 `"1,234,000"` 같은 값)

```python
for col in ["총상환원금", "총상환이자"]:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", ""), errors="coerce"
    )
df["총상환금액"] = df["총상환원금"] + df["총상환이자"]
```

문자열끼리 `+` 하면 오류 없이 **`"100" + "200" = "100200"`** 이 됩니다.
이것도 조용히 틀리는 대표 사례입니다.

---

## 정리: 기존 실습에서 이어지는 학습 경로

| 기존 실습 | 이어서 볼 예제 | 무엇이 달라지나 |
|---|---|---|
| 중복 제거 | [01](../../examples/01-dedup-latest/) | 키 기준 최신값 유지, 제거분 검증 |
| 결측/0 처리 | [02](../../examples/02-missing-and-zero/), [08](../../examples/08-impute-smart/) | 컬럼별 처리 분리, 대치와 흔적 남기기 |
| 값 치환·파생 | [03](../../examples/03-replace-and-derive/) | `np.select` 다중 조건, 규격 판정 |
| 조인 + 분리 | [04](../../examples/04-join-and-split/) | 조인 진단, 누락 방지, 빈 결과 방어 |
| — | [05](../../examples/05-wide-to-long/) 이후 | Spotfire로는 아예 불가능한 영역 |

기존 실습은 **"데이터 함수가 무엇인지"** 를 가르치기에 최적입니다.
이 교안의 05번 이후 예제들은 **"왜 데이터 함수를 써야 하는지"** 를 보여 주는 것이 목적입니다.
두 가지를 순서대로 진행하는 것을 권장합니다.

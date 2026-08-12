---
title: 결과 검증하기
parent: AI 활용법
nav_order: 3
---

# 결과 검증하기
{: .no_toc }

AI가 준 코드에서 **가장 위험한 것은 오류가 나는 코드가 아니라, 오류 없이 조용히 틀리는 코드**입니다.
오류는 화면에 뜨지만, 틀린 숫자는 보고서까지 갑니다.
{: .fs-5 .fw-300 }

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## 30초 검증 4단계

코드를 받아 실행한 뒤 **항상** 이 네 가지를 확인하세요.

### ① 행 수가 말이 되는가

| 처리 | 기대되는 행 수 |
|---|---|
| 필터/삭제 | 원본보다 **작다** |
| 컬럼 추가/파생 | 원본과 **같다** |
| 그룹 집계 | **그룹 수**와 같다 |
| 조인 | 보통 왼쪽 테이블과 같다 — **늘었다면 키 중복** |
| melt(Wide→Long) | 원본 행 수 **×** 값 컬럼 수 |

{: .주의 }
> **조인 후 행 수가 늘었다면 거의 100% 버그입니다.** 오른쪽 테이블의 키 중복을 확인하세요.

### ② 합계가 보존되는가

구조만 바꾸는 처리(피벗, melt, 그룹 집계)는 **총합이 변하지 않아야** 합니다.

```python
print(before["AMOUNT"].sum(), after["AMOUNT"].sum())    # 같아야 정상
```

파레토나 ABC 분석이라면 **비중의 합이 100%** 인지 확인하세요.

### ③ 결측이 늘지 않았는가

조인 실패, 타입 변환 실패, 정렬 어긋남은 전부 **결측 증가**로 나타납니다.

```python
before.isna().sum().sum()   # 처리 전
after.isna().sum().sum()    # 처리 후 — 이유 없이 늘었다면 조사
```

### ④ 샘플 몇 건을 손으로 확인

가장 확실한 방법입니다. **특정 LOT 하나를 골라 손으로 계산**해 보세요.
그룹 평균 하나, 판정 결과 한 줄이면 충분합니다.

---

## 조용히 틀리는 대표 유형 8가지

### 1. 정렬을 빼먹은 시계열 계산

이동평균·`shift`·`diff`·누적합은 **정렬에 전적으로 의존**합니다.
정렬하지 않아도 오류는 나지 않고, **그럴듯한 틀린 값**이 나옵니다.

```python
df = df.sort_values(["EQP_ID", "MEAS_TIME"])   # 반드시 먼저
```

### 2. 그룹 경계를 넘는 계산

`shift()`, `diff()`, `rolling()` 을 그룹 구분 없이 쓰면 **A설비의 마지막 값과 B설비의 첫 값**이 계산됩니다.

```python
df["DIFF"] = df["X"].diff()                        # ❌ 그룹 경계를 넘음
df["DIFF"] = df.groupby("EQP_ID")["X"].diff()      # ✅
```

### 3. 0을 정상값으로 취급

`PRESSURE = 0` 은 센서 미취득인데 평균에 포함되면 평균이 낮아집니다.
반대로 `PARTICLE_CNT = 0` 을 결측 취급해 지우면 **양품 데이터가 통째로 사라집니다.**

### 4. `dropna()` 의 기본 동작

`df.dropna()` 는 **한 컬럼이라도 비면 그 행을 삭제**합니다.
컬럼이 20개인 테이블에서는 절반 이상이 사라지기도 합니다. 항상 `subset=` 을 쓰세요.

### 5. 인덱스 불일치

정렬·필터 후 `reset_index()` 를 안 한 상태로 다른 Series를 대입하면
**인덱스 기준으로 정렬되어 엉뚱한 행에 값이 들어갑니다.** 오류는 안 납니다.

```python
result = result.reset_index(drop=True)
```

### 6. 문자열 키 불일치

`"ETC01 "` 과 `"etc01"` 과 `"ETC01"` 은 전부 다른 값입니다.
조인이 조용히 실패하고 결과가 비어 버립니다.

### 7. 표본이 너무 적은 그룹

표본 3개짜리 그룹의 Cpk, 표준편차, 회귀 기울기는 **숫자는 나오지만 의미가 없습니다.**
반드시 최소 표본 수 조건을 넣고, 미달 그룹은 **계산하지 말고 표시**하세요.

### 8. 그룹 키가 통째로 사라짐

**오류 없이 데이터가 사라지는 가장 흔한 경로**입니다.
인덱스는 Spotfire로 전달되지 않으므로, `groupby()` 결과를 그대로 내보내면
그룹 키 컬럼이 없어집니다. 값만 남아 어느 설비 것인지 알 수 없게 됩니다.

```python
output = df.groupby("EQP_ID")["THICKNESS"].mean()                  # ❌ EQP_ID 소실
output = df.groupby("EQP_ID", as_index=False)["THICKNESS"].mean()  # ✅
```

`pivot_table()`, `value_counts()`, `describe()`, `agg()` 전부 해당합니다.

---

## 검증용 데이터 함수

의심스러울 때 실행해 보는 범용 점검 함수입니다.

```python
import pandas as pd

df = input
rows = []
for c in df.columns:
    s = df[c]
    first = s.dropna().iloc[0] if s.notna().any() else None
    rows.append({
        "COLUMN": c,
        "DTYPE": str(s.dtype),
        "VALUE_TYPE": type(first).__name__ if first is not None else "-",   # object 의 정체
        "N": int(s.size),
        "NULL": int(s.isna().sum()),
        "NULL_PCT": round(float(s.isna().mean() * 100), 2),
        "NUNIQUE": int(s.nunique(dropna=True)),
        "ZERO_CNT": int((s == 0).sum()) if pd.api.types.is_numeric_dtype(s) else 0,
        "MIN": str(s.min()) if pd.api.types.is_numeric_dtype(s) else "",
        "MAX": str(s.max()) if pd.api.types.is_numeric_dtype(s) else "",
        "SAMPLE": ", ".join(str(v) for v in s.dropna().head(3).tolist()),
    })

output = pd.DataFrame(rows)
```

이 표에서 확인할 것:

- `NULL_PCT` 가 갑자기 높은 컬럼 → 조인 실패 또는 변환 실패
- `ZERO_CNT` 가 많은 숫자 컬럼 → **0이 결측 아닌지** 확인
- `NUNIQUE` 가 1 → 상수 컬럼, 계산에서 문제를 일으킬 수 있음
- `DTYPE` 이 `object` 인데 숫자처럼 보임 → 타입 변환 누락
- **`VALUE_TYPE` 이 `datetime` 인데 `DTYPE` 이 `object`** → Spotfire DateTime 컬럼.
  `pd.to_datetime()` 을 거치지 않으면 `.dt` 가 실패합니다

{: .팁 }
> 이 점검을 정규화까지 포함해 완성한 것이
> [25번 예제(입력 타입 진단기)](../../examples/25-input-type-doctor/)입니다.
> 라이브러리에 저장해 두고 새 데이터를 만날 때마다 돌려 보세요.

---

## AI에게 검증을 시키는 프롬프트

코드를 **작성한 뒤 다시 한 번 검토**를 요청하면 실제로 문제를 잘 찾아냅니다.

````text
아래 코드를 비판적으로 검토해줘. 의도는 [무엇]이야.

```python
(코드)
```

특히 아래 관점에서 문제를 찾아줘:
1. 정렬이 필요한데 빠진 곳
2. 그룹 경계를 넘어 계산되는 곳 (shift/diff/rolling)
3. 0으로 나누기 가능성
4. 결측이 있을 때 결과가 왜곡되는 지점
5. 표본이 적은 그룹에서 의미 없는 값이 나오는 지점
6. Spotfire 입력 타입 가정 오류
   (DateTime/Boolean 컬럼은 object dtype 인데 .dt 나 불리언 연산을 바로 쓴 곳)
7. Spotfire 출력 시 문제가 될 부분
   (빈 결과, 전부 결측인 컬럼, 문자열 아닌 컬럼명, 인덱스에 남아 있는 그룹 키)
8. 100만 행에서 느려질 지점

문제가 없다면 '없음'이라고 말하고, 있다면 수정 코드를 제시해줘.
````

{: .팁 }
> **다른 AI 모델에게 교차 검토를 시키는 것도 효과적입니다.**
> A모델이 만든 코드를 B모델에게 검토시키면 서로 다른 관점의 문제를 잡아냅니다.

---

## 운영에 올리기 전 최종 체크리스트

- [ ] 행 수·합계·결측이 예상대로인가
- [ ] 샘플 몇 건을 손으로 확인했는가
- [ ] 입력이 **0행**일 때 죽지 않는가 (마킹 비었을 때)
- [ ] 특정 그룹의 표본이 1개일 때 죽지 않는가
- [ ] 컬럼이 없을 때 **의미 있는 오류 메시지**가 나오는가
- [ ] 실행 시간이 허용 범위인가 (자동 재계산이면 특히)
- [ ] 결과 테이블의 컬럼명이 전부 문자열인가
- [ ] **그룹 키가 컬럼으로 나와 있는가** (인덱스에 숨어 있지 않은가)
- [ ] **전부 결측인 컬럼이 없는가** (있다면 `set_spotfire_types` 로 타입 지정했는가)
- [ ] 서버(Web Player)에서도 쓸 분석이라면 **추가 패키지가 서버에 배포되어 있는가**
- [ ] 코드를 **내가 설명할 수 있는가** ← 가장 중요

{: .주의 }
> **마지막 항목이 가장 중요합니다.**
> 이해하지 못한 코드는 운영에 올리지 마세요.
> 이해가 안 되면 AI에게 "이 줄이 무엇을 하는지 초보자에게 설명해줘"라고 물으면 됩니다.
> 그 과정 자체가 이 교육의 목표입니다.

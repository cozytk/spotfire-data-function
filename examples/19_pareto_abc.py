'''---
title: 파레토 분석과 ABC 등급 분류
level: 4
difficulty: ★★☆
summary: 누적 기여율을 계산해 "상위 몇 개가 전체의 80%를 차지하는가"에 답하고, A/B/C 등급을 자동으로 매깁니다.
data: [sales_orders.csv]
inputs:
  input:
    file: sales_orders.csv
  a_cut: 0.8
  b_cut: 0.95
outputs: [output, output_summary]
---
## 시나리오

- 영업/SCM: "매출의 80%를 만드는 고객은 몇 개사인가?" → 관리 등급 A/B/C
- 품질: "전체 불량의 80%를 차지하는 불량 유형은?" → 개선 과제 우선순위

둘 다 **동일한 계산**입니다. 정렬 → 누적합 → 누적 비율 → 등급.

## 왜 Spotfire 기본 기능으로는 어려운가

- **누적합(cumulative sum)이 정렬 순서에 의존**한다는 것이 문제입니다.
  Spotfire의 `Cumulative Sum` 은 시각화의 축 정렬을 따라가므로, 정렬을 바꾸면 결과가 바뀝니다.
  "금액 내림차순 기준 누적 비율"을 **데이터로 고정**하기 어렵습니다.
- **80% 경계에서 등급을 자르는 로직**을 표현식으로 만들면, 그 등급을 다시 다른 테이블과 조인할 수 없습니다.
- 데이터 함수는 등급이 **컬럼으로 확정**되어 조인·필터·색상에 자유롭게 씁니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `sales_orders` |
| 입력 | `a_cut` | Value (Real) | A등급 누적 기준 (기본 0.8) |
| 입력 | `b_cut` | Value (Real) | B등급 누적 기준 (기본 0.95) |
| 출력 | `output` | Table | 고객별 파레토/ABC 등급 |
| 출력 | `output_summary` | Table | 등급별 요약 |

## 스크립트

{{CODE}}

## 핵심 포인트

- 파레토의 공식은 딱 4줄입니다. 어떤 축에도 그대로 적용됩니다.

  ```python
  s = df.sort_values("금액", ascending=False)
  s["CUM"]     = s["금액"].cumsum()
  s["CUM_PCT"] = s["CUM"] / s["금액"].sum()
  s["GRADE"]   = np.select([s["CUM_PCT"] <= 0.8, s["CUM_PCT"] <= 0.95], ["A", "B"], "C")
  ```

- **경계 처리에 주의하세요.** `누적비율 <= 0.8` 로 자르면 80%를 처음 넘긴 항목이 B가 됩니다.
  일반적으로는 **그 항목까지 A에 포함**하는 것이 맞습니다(80%를 "채우는" 마지막 항목이므로).
  이 예제는 `shift()` 로 직전 누적비율을 보고 그 처리를 반영했습니다. 실무에서 자주 틀리는 부분입니다.
- 취소 주문 등 **집계에서 빼야 할 행을 먼저 걸러 내세요.** 이 필터를 빠뜨리면 등급이 통째로 왜곡됩니다.
- 등급 컷은 **문서 속성으로 빼세요.** 조직마다 70/90, 80/95 등 기준이 다릅니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input(주문 데이터), a_cut(0.8), b_cut(0.95).
컬럼: ORDER_ID, ORDER_DATE, CUSTOMER, REGION, PRODUCT_FAMILY, QTY, AMOUNT_USD, STATUS

1. STATUS 가 'CANCELLED' 인 주문은 제외
2. CUSTOMER 별 총 매출액/주문건수/평균단가 집계
3. 매출액 내림차순으로 파레토 계산: 누적금액, 누적비율, 전체 대비 비중, 순위
4. ABC 등급 부여. 단 누적비율이 a_cut 을 처음 넘는 고객까지는 A 등급에 포함할 것
   (직전 누적비율 기준으로 판정)
5. 등급별 요약(고객수, 매출합, 매출비중, 고객수비중)도 만들어줘
출력: output, output_summary
```

## 확인 & 응용

- `output_summary` 에서 "A등급 고객 수 비중 20% / 매출 비중 80%"가 나오면 교과서적인 파레토입니다.
- **응용**: `wafer_yield.csv` 의 `MAIN_FAIL_TYPE` 별 불량 die 수로 같은 코드를 돌리면
  **품질 개선 과제 우선순위**가 나옵니다. 집계 대상 컬럼만 바꾸면 됩니다.
- **응용**: `REGION` 별로 나눠 지역별 파레토를 만들어 보세요 (`groupby` 안에서 동일 로직 반복).
'''
import numpy as np
import pandas as pd

df = input.copy()

# 1) 집계 대상이 아닌 행 제외 — 이걸 빠뜨리면 등급이 통째로 왜곡된다
df = df[df["STATUS"] != "CANCELLED"]

# 2) 고객별 집계
agg = (
    df.groupby("CUSTOMER", as_index=False)
    .agg(
        AMOUNT=("AMOUNT_USD", "sum"),
        ORDERS=("ORDER_ID", "nunique"),
        QTY=("QTY", "sum"),
        REGION=("REGION", lambda s: s.mode().iloc[0] if not s.mode().empty else ""),
        FIRST_ORDER=("ORDER_DATE", "min"),
        LAST_ORDER=("ORDER_DATE", "max"),
    )
)
agg["AVG_PRICE"] = (agg["AMOUNT"] / agg["QTY"]).round(3)

# 3) 파레토 : 정렬 -> 누적합 -> 누적비율
agg = agg.sort_values("AMOUNT", ascending=False).reset_index(drop=True)
total = agg["AMOUNT"].sum()
agg["RANK"] = np.arange(1, len(agg) + 1)
agg["SHARE_PCT"] = (agg["AMOUNT"] / total * 100).round(3)
agg["CUM_AMOUNT"] = agg["AMOUNT"].cumsum()
agg["CUM_PCT"] = (agg["CUM_AMOUNT"] / total).round(6)

# 4) ABC 등급 : '직전 누적비율'로 판정해야 경계 항목이 올바른 등급에 들어간다
prev_cum = agg["CUM_PCT"].shift(fill_value=0.0)
agg["GRADE"] = np.select(
    [prev_cum < float(a_cut), prev_cum < float(b_cut)],
    ["A", "B"],
    default="C",
)
agg["CUM_PCT"] = (agg["CUM_PCT"] * 100).round(3)

# 5) 등급별 요약
summary = (
    agg.groupby("GRADE", as_index=False)
    .agg(CUSTOMERS=("CUSTOMER", "nunique"), AMOUNT=("AMOUNT", "sum"), ORDERS=("ORDERS", "sum"))
    .sort_values("GRADE")
)
summary["CUSTOMER_PCT"] = (summary["CUSTOMERS"] / len(agg) * 100).round(2)
summary["AMOUNT_PCT"] = (summary["AMOUNT"] / total * 100).round(2)
summary["AMOUNT"] = summary["AMOUNT"].round(2)
summary["INTERPRETATION"] = (
    summary["CUSTOMER_PCT"].astype(str) + "% 고객이 매출의 " + summary["AMOUNT_PCT"].astype(str) + "% 차지"
)

agg["AMOUNT"] = agg["AMOUNT"].round(2)
agg["CUM_AMOUNT"] = agg["CUM_AMOUNT"].round(2)

output = agg
output_summary = summary.reset_index(drop=True)

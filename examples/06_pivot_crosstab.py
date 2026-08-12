'''---
title: 피벗 / 크로스탭 — 설비 × 챔버 불량률 매트릭스
level: 2
difficulty: ★★☆
summary: pivot_table 로 집계 매트릭스를 만들고, 합계행·합계열까지 붙여 새 데이터 테이블로 내보냅니다.
data: [fab_measurement.csv]
inputs:
  input:
    file: fab_measurement.csv
outputs: [output, output_long]
---
## 시나리오

"설비별 × 챔버별 불량률을 한 장의 표로 보고, 그 표를 **데이터로도** 쓰고 싶다"는 요구입니다.
크로스탭 시각화로 화면에 보는 것과, 그 결과를 **다른 분석의 입력 데이터로 쓰는 것**은 전혀 다른 이야기입니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- 크로스탭 시각화는 **보여 주기만** 합니다. 그 결과를 다른 시각화의 입력이나 조인 대상으로 쓸 수 없습니다.
  (내보내기 → 다시 불러오기를 수동으로 반복하게 됩니다.)
- "불량률 = `IS_DEFECT='TRUE'` 인 비율" 처럼 **비율 집계**는 계산 컬럼 + 커스텀 집계를 조합해야 합니다.
- **합계행/합계열(margins)** 과 "전체 대비 기여율"을 같이 넣으려면 표현식이 급격히 복잡해집니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 출력 | `output` | Table | 설비 × 챔버 불량률 매트릭스 (Wide) |
| 출력 | `output_long` | Table | 같은 내용의 Long 포맷 (히트맵용) |

## 스크립트

{{CODE}}

## 핵심 포인트

- `pivot_table(index=행, columns=열, values=값, aggfunc=집계함수)` 가 기본형입니다.
- `aggfunc` 에 **직접 만든 함수**를 넣을 수 있는 게 핵심입니다. 여기서는 불량률(`mean of boolean`)을 썼습니다.
- `margins=True, margins_name="합계"` 로 합계행·합계열을 자동 생성합니다.
- pivot 결과는 **행 인덱스와 다단 컬럼(MultiIndex)** 을 갖습니다. Spotfire로 내보내기 전에 반드시
  `reset_index()` 로 인덱스를 컬럼으로 되돌리고, 컬럼명을 **문자열로 평탄화**해야 합니다.
  이걸 빠뜨리면 "컬럼명이 문자열이 아니다" 류의 오류를 만납니다.
- 히트맵을 그릴 거라면 Wide보다 **Long 포맷이 편합니다.** 그래서 두 벌 다 출력했습니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수.
입력 input 컬럼: EQP_ID, CHAMBER, STEP_DESC, IS_DEFECT('TRUE'/'FALSE'/'REAL'), PARTICLE_CNT
1. IS_DEFECT 를 불리언으로 정리 ('REAL'과 'TRUE'는 True)
2. 행=EQP_ID, 열=CHAMBER 로 불량률(%) 피벗 테이블 생성, 소수 둘째 자리 반올림
3. 합계행/합계열 포함
4. MultiIndex 를 평탄화하고 컬럼명을 모두 문자열로 만들어 Spotfire 로 내보낼 수 있게 할 것
5. 같은 결과를 (EQP_ID, CHAMBER, DEFECT_RATE) long 포맷으로도 출력
출력: output(wide), output_long(long)
```

## 확인 & 응용

- Long 결과로 히트맵(색: `DEFECT_RATE`)을 만들면 문제 설비-챔버 조합이 바로 보입니다.
- **응용**: `values` 를 `PARTICLE_CNT` 로, `aggfunc` 를 `"median"` 으로 바꿔 비교해 보세요.
- **응용**: `hr_training.csv` 로 부서 × 과정 카테고리별 평균 이수시간 매트릭스를 만들어 보세요.
'''
import pandas as pd

df = input.copy()

# 1) 불량 여부를 불리언으로 정리
df["IS_DEFECT_BOOL"] = df["IS_DEFECT"].astype(str).str.upper().isin(["TRUE", "REAL", "Y", "1"])

# 2) 설비 × 챔버 불량률(%) 피벗 — aggfunc 에 "평균"을 주면 비율이 된다
pv = df.pivot_table(
    index="EQP_ID",
    columns="CHAMBER",
    values="IS_DEFECT_BOOL",
    aggfunc="mean",
    margins=True,
    margins_name="합계",
)
pv = (pv * 100).round(2)

# 3) Spotfire 로 내보내기 전 필수 정리 : 인덱스 해제 + 컬럼명 문자열화
pv = pv.reset_index()
pv.columns = [str(c) for c in pv.columns]
pv.columns.name = None

# 4) 히트맵용 Long 포맷 (합계 행/열은 제외)
long_df = (
    df.groupby(["EQP_ID", "CHAMBER"], as_index=False)
    .agg(N=("IS_DEFECT_BOOL", "size"), DEFECT_CNT=("IS_DEFECT_BOOL", "sum"))
)
long_df["DEFECT_RATE"] = (long_df["DEFECT_CNT"] / long_df["N"] * 100).round(2)

output = pv
output_long = long_df

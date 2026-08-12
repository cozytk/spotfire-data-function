'''---
title: 설비 간 차이가 진짜인가 — ANOVA와 사후 다중비교
level: 4
difficulty: ★★★
summary: 눈으로 보면 달라 보이는 그룹 평균이 통계적으로 유의한지 검정하고, 어느 쌍이 다른지까지 짚어 냅니다.
data: [fab_measurement.csv]
inputs:
  input:
    file: fab_measurement.csv
  alpha: 0.05
packages: [scipy]
outputs: [output_anova, output_posthoc]
---
## 시나리오

박스플롯을 보니 설비 A와 B의 두께 분포가 달라 보입니다. 회의에서 반드시 나오는 질문:

> "그거 그냥 산포 아니에요?"

이 질문에 **p-value로 답하는 것**과 "그래 보입니다"로 답하는 것은 완전히 다릅니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire에는 통계 검정 기능이 **기본 제공되지 않습니다.** (별도 도구/확장이 필요합니다.)
- 박스플롯은 분포를 보여 줄 뿐 **유의성을 말해 주지 않습니다.**
- 사후 다중비교(어느 쌍이 다른가)는 쌍 개수만큼 검정을 반복하고 **다중검정 보정**까지 해야 합니다.
- AI에게는 "일원분산분석하고 Bonferroni 보정한 사후검정 해줘"라고 하면 끝납니다.
  **통계 용어가 곧 사양**이 되는, AI 활용 효과가 가장 큰 영역입니다.

## ⚠️ 패키지 안내

이 예제는 **`scipy`** 가 필요합니다. Spotfire에 기본 번들된 패키지가 아닐 수 있으니
`도구 > Python 도구 > 패키지 관리` 에서 설치 여부를 먼저 확인하세요.
설치가 어려운 환경이라면 `numpy` 만으로 F 통계량까지는 계산할 수 있지만, p-value 계산에는 분포 함수가 필요합니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 입력 | `alpha` | Value (Real) | 문서 속성 `Alpha` (기본 0.05) |
| 출력 | `output_anova` | Table | 공정별 ANOVA 결과 |
| 출력 | `output_posthoc` | Table | 설비 쌍별 사후검정 결과 |

## 스크립트

{{CODE}}

## 핵심 포인트

- **ANOVA는 "적어도 한 그룹이 다르다"까지만** 말해 줍니다. 어느 쌍이 다른지는 사후검정이 필요합니다.
- 사후검정에서 **다중검정 보정은 필수**입니다. 10번 검정하면 우연히 유의한 결과가 나올 확률이 40%에 이릅니다.
  가장 간단하고 보수적인 방법이 **Bonferroni**(α를 비교 횟수로 나눔)입니다.
- **Welch t-test(`equal_var=False`)** 를 기본으로 쓰세요. 분산이 같다는 가정을 하지 않아 더 안전합니다.
- **표본이 크면 p-value는 거의 항상 유의해집니다.** 그래서 **효과크기(Cohen's d)** 를 함께 봐야 합니다.
  - |d| < 0.2 미미 / 0.2~0.5 작음 / 0.5~0.8 중간 / 0.8 이상 큼
  - "통계적으로 유의하지만 실무적으로는 무시 가능"한 경우를 걸러 내는 장치입니다.
- 정규성·등분산 가정이 의심되면 비모수 검정(`kruskal`, `mannwhitneyu`)으로 교차 확인하세요.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. scipy.stats 사용.
입력: input(DataFrame), alpha(float, 유의수준)
컬럼: STEP_DESC, EQP_ID, CHAMBER, THICKNESS

1. STEP_DESC 별로, EQP_ID 를 그룹으로 하는 일원분산분석(one-way ANOVA)을 수행해줘.
   - 그룹이 2개 미만이거나 표본 30개 미만인 그룹은 제외
   - 결과: STEP_DESC, 그룹수, 전체 N, F통계량, P_VALUE, 유의여부(alpha 기준), 판정 문구
   - 비모수 교차검증으로 Kruskal-Wallis 결과도 같은 행에 포함
2. 유의한 STEP_DESC 에 대해 설비 쌍별 Welch t-test 사후검정을 해줘.
   - Bonferroni 보정 적용 (P_ADJ = min(1, P * 비교횟수))
   - Cohen's d 효과크기와 해석(미미/작음/중간/큼) 포함
   - 평균 차이, 각 그룹 평균/표본수 포함
3. 결과가 비면 안내용 1행을 넣어 빈 테이블이 나가지 않게 해줘
출력: output_anova, output_posthoc
```

## 확인 & 응용

- `output_posthoc` 을 `P_ADJ` 오름차순 + `EFFECT_SIZE` 내림차순으로 보면 **조치 우선순위**가 나옵니다.
- **응용**: 그룹을 `CHAMBER` 로 바꾸면 챔버 간 차이 검정이 됩니다.
- **응용**: `iris.csv` 로 품종별 꽃잎 길이 차이를 검정해 보세요. 교육용으로 결과가 아주 깔끔합니다.
'''
import itertools

import numpy as np
import pandas as pd
from scipy import stats

df = input.copy().dropna(subset=["THICKNESS"])
ALPHA = float(alpha)
MIN_N = 30

anova_rows = []
posthoc_rows = []

for step, block in df.groupby("STEP_DESC"):
    # 표본이 충분한 그룹만 검정 대상
    counts = block.groupby("EQP_ID")["THICKNESS"].size()
    valid_eqp = counts[counts >= MIN_N].index.tolist()
    if len(valid_eqp) < 2:
        continue

    groups = [block.loc[block["EQP_ID"] == e, "THICKNESS"].to_numpy() for e in valid_eqp]

    f_stat, p_anova = stats.f_oneway(*groups)
    h_stat, p_kruskal = stats.kruskal(*groups)      # 비모수 교차검증

    anova_rows.append(
        {
            "STEP_DESC": step, "N_GROUPS": len(groups), "N_TOTAL": int(sum(len(g) for g in groups)),
            "F_STAT": round(float(f_stat), 4), "P_VALUE": float(p_anova),
            "KRUSKAL_H": round(float(h_stat), 4), "P_KRUSKAL": float(p_kruskal),
            "SIGNIFICANT": bool(p_anova < ALPHA),
            "VERDICT": "설비 간 차이 있음" if p_anova < ALPHA else "차이 있다고 볼 수 없음",
        }
    )

    if p_anova >= ALPHA:
        continue

    # --- 사후검정 : 모든 설비 쌍에 대해 Welch t-test + Bonferroni 보정 ---
    pairs = list(itertools.combinations(range(len(valid_eqp)), 2))
    n_comp = len(pairs)
    for i, j in pairs:
        a, b = groups[i], groups[j]
        t_stat, p_raw = stats.ttest_ind(a, b, equal_var=False)   # Welch : 등분산 가정 안 함

        # Cohen's d (합동 표준편차 기준 효과크기)
        pooled_sd = np.sqrt(((len(a) - 1) * a.std(ddof=1) ** 2 + (len(b) - 1) * b.std(ddof=1) ** 2)
                            / (len(a) + len(b) - 2))
        d = (a.mean() - b.mean()) / pooled_sd if pooled_sd > 0 else np.nan
        p_adj = min(1.0, float(p_raw) * n_comp)

        posthoc_rows.append(
            {
                "STEP_DESC": step, "EQP_A": valid_eqp[i], "EQP_B": valid_eqp[j],
                "N_A": len(a), "N_B": len(b),
                "MEAN_A": round(float(a.mean()), 3), "MEAN_B": round(float(b.mean()), 3),
                "MEAN_DIFF": round(float(a.mean() - b.mean()), 3),
                "T_STAT": round(float(t_stat), 4), "P_VALUE": float(p_raw), "P_ADJ": p_adj,
                "SIGNIFICANT": bool(p_adj < ALPHA),
                "COHENS_D": round(float(d), 4),
                "EFFECT_SIZE": ("큼" if abs(d) >= 0.8 else "중간" if abs(d) >= 0.5
                                else "작음" if abs(d) >= 0.2 else "미미"),
            }
        )

anova = pd.DataFrame(anova_rows)
posthoc = pd.DataFrame(posthoc_rows)

if anova.empty:
    anova = pd.DataFrame([{"STEP_DESC": "NO_DATA", "N_GROUPS": 0, "N_TOTAL": 0, "F_STAT": 0.0,
                           "P_VALUE": 1.0, "KRUSKAL_H": 0.0, "P_KRUSKAL": 1.0,
                           "SIGNIFICANT": False, "VERDICT": "검정 대상 없음"}])
if posthoc.empty:
    posthoc = pd.DataFrame([{"STEP_DESC": "NO_DATA", "EQP_A": "-", "EQP_B": "-", "N_A": 0, "N_B": 0,
                             "MEAN_A": 0.0, "MEAN_B": 0.0, "MEAN_DIFF": 0.0, "T_STAT": 0.0,
                             "P_VALUE": 1.0, "P_ADJ": 1.0, "SIGNIFICANT": False,
                             "COHENS_D": 0.0, "EFFECT_SIZE": "미미"}])

output_anova = anova.sort_values("P_VALUE").reset_index(drop=True)
output_posthoc = posthoc.sort_values(["P_ADJ", "COHENS_D"]).reset_index(drop=True)

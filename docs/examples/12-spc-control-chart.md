---
title: 12. SPC 관리도 + 공정능력지수(Cp/Cpk) + Western Electric 룰
parent: 예제 모음
nav_order: 12
---

# 12. SPC 관리도 + 공정능력지수(Cp/Cpk) + Western Electric 룰
{: .no_toc }

**난이도** ★★★ · **Level 3 · 시계열과 공정 분석**

관리한계선을 직접 계산하고, 8개 룰 중 4개를 구현해 "관리 이탈" 시점을 자동으로 찾아냅니다. 데이터 함수의 진가가 가장 잘 드러나는 예제.

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/12_spc_control_chart.py)

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
| 입력 | `sigma_k` | Value | 문서 속성 (예: `3.0`) |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_capability` | Table | 새 데이터 테이블 |
| 출력 | `output_violation` | Table | 새 데이터 테이블 |

---

## 시나리오

품질/공정 담당이 매일 보는 화면입니다.

1. 설비·공정별 **관리도(Control Chart)**: 중심선(CL), 관리상한(UCL), 관리하한(LCL)
2. **공정능력지수** Cp / Cpk / Pp / Ppk
3. **Western Electric 룰 위반 지점** — 관리한계 안에 있어도 패턴이 이상하면 잡아내는 규칙

## 왜 Spotfire 기본 기능으로는 어려운가

이 예제가 "기본 기능으로는 복잡한데 AI로 코드를 얻으면 쉬운"의 대표 사례입니다.

- **관리한계선**: `Avg ± 3×StdDev` 는 표현식으로 되지만, 개별값 관리도(I-MR)의 표준 방식인
  **이동범위(MR) 기반 σ̂ = MR̄ / 1.128** 은 표현식으로 만들기 매우 번거롭습니다.
- **Cpk**: `min((USL-μ)/3σ, (μ-LSL)/3σ)` — 규격을 공정별로 다르게 적용해야 해 표현식이 폭발합니다.
- **Western Electric 룰**: "연속 9점이 중심선 한쪽", "연속 3점 중 2점이 2σ 밖", "연속 6점 연속 상승"…
  → **연속성 판정**은 Spotfire 표현식으로는 사실상 불가능합니다. 이게 결정적입니다.
- 반면 AI에게는 "Western Electric Rule 1,2,3,5를 구현해줘"라고 말하면 됩니다. **이름이 곧 사양**이니까요.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 입력 | `sigma_k` | Value (Real) | 문서 속성 `SigmaK` (기본 3.0) |
| 출력 | `output` | Table | 관리도용 데이터 (CL/UCL/LCL/룰위반) |
| 출력 | `output_capability` | Table | 그룹별 Cp/Cpk/Pp/Ppk 요약 |
| 출력 | `output_violation` | Table | 룰 위반 지점만 추출 |

## 스크립트

```python
import numpy as np
import pandas as pd

df = input.copy()
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])
df = df.dropna(subset=["THICKNESS"])
df = df.sort_values(["EQP_ID", "STEP_DESC", "MEAS_TIME"]).reset_index(drop=True)

GROUP = ["EQP_ID", "STEP_DESC"]
VALUE = "THICKNESS"
MIN_N = 30
D2 = 1.128  # 개별값 관리도(n=2 이동범위)용 상수

# 공정별 규격
SPEC = {"PC": (520.0, 0.03), "RMG": (310.0, 0.03), "CBCMP": (980.0, 0.02),
        "ETCH": (145.0, 0.05), "PHOTO": (88.0, 0.05)}
df["USL"] = df["STEP_DESC"].map(lambda s: SPEC[s][0] * (1 + SPEC[s][1]) if s in SPEC else np.nan)
df["LSL"] = df["STEP_DESC"].map(lambda s: SPEC[s][0] * (1 - SPEC[s][1]) if s in SPEC else np.nan)

g = df.groupby(GROUP)[VALUE]

# --- 관리한계선 -------------------------------------------------------------
df["CL"] = g.transform("mean")
df["MR"] = g.transform(lambda s: s.diff().abs())          # 이동범위
mr_bar = df.groupby(GROUP)["MR"].transform("mean")
df["SIGMA_HAT"] = (mr_bar / D2).replace(0, np.nan)         # 군내 변동 추정
df["SIGMA_ALL"] = g.transform("std").replace(0, np.nan)    # 전체 산포

k = float(sigma_k)
df["UCL"] = df["CL"] + k * df["SIGMA_HAT"]
df["LCL"] = df["CL"] - k * df["SIGMA_HAT"]
df["GRP_N"] = g.transform("size")

# 중심선 기준 편차를 시그마 단위로 (룰 판정의 공통 재료)
z = (df[VALUE] - df["CL"]) / df["SIGMA_HAT"]
df["SIGMA_Z"] = z.round(3)
above = z > 0

# --- Western Electric 룰 ----------------------------------------------------
gb = df.groupby(GROUP)

# Rule 1 : 1점이 3시그마 밖
df["RULE1"] = z.abs() > 3

# Rule 2 : 연속 9점이 중심선의 같은 쪽
df["_ABOVE"] = above.astype(float)
run_up = gb["_ABOVE"].transform(lambda s: s.rolling(9).sum())
df["RULE2"] = (run_up == 9) | (run_up == 0)

# Rule 3 : 연속 6점이 계속 상승 또는 계속 하강
df["_INC"] = (gb[VALUE].transform(lambda s: s.diff()) > 0).astype(float)
df["_DEC"] = (gb[VALUE].transform(lambda s: s.diff()) < 0).astype(float)
inc6 = gb["_INC"].transform(lambda s: s.rolling(5).sum())
dec6 = gb["_DEC"].transform(lambda s: s.rolling(5).sum())
df["RULE3"] = (inc6 == 5) | (dec6 == 5)

# Rule 5 : 연속 3점 중 2점이 같은 쪽 2시그마 밖
df["_HI2"] = (z > 2).astype(float)
df["_LO2"] = (z < -2).astype(float)
hi = gb["_HI2"].transform(lambda s: s.rolling(3).sum())
lo = gb["_LO2"].transform(lambda s: s.rolling(3).sum())
df["RULE5"] = (hi >= 2) | (lo >= 2)

RULES = ["RULE1", "RULE2", "RULE3", "RULE5"]
df[RULES] = df[RULES].fillna(False).astype(bool)
df["RULE_VIOLATED"] = df[RULES].any(axis=1)
df["RULE_NAMES"] = [
    ",".join([r for r, v in zip(RULES, row) if v]) or "OK" for row in df[RULES].to_numpy()
]

# 표본이 적은 그룹은 판정하지 않는다
insufficient = df["GRP_N"] < MIN_N
df.loc[insufficient, RULES + ["RULE_VIOLATED"]] = False
df.loc[insufficient, "RULE_NAMES"] = "표본부족"

# --- 공정능력지수 -----------------------------------------------------------
cap = df.groupby(GROUP, as_index=False).agg(
    N=(VALUE, "size"), MEAN=(VALUE, "mean"), STD_ALL=(VALUE, "std"),
    SIGMA_HAT=("SIGMA_HAT", "first"), USL=("USL", "first"), LSL=("LSL", "first"),
)
for sig_col, prefix in [("SIGMA_HAT", "C"), ("STD_ALL", "P")]:
    s = cap[sig_col].replace(0, np.nan)
    cap[f"{prefix}p"] = (cap["USL"] - cap["LSL"]) / (6 * s)
    cap[f"{prefix}pk"] = np.minimum(
        (cap["USL"] - cap["MEAN"]) / (3 * s), (cap["MEAN"] - cap["LSL"]) / (3 * s)
    )

cap["JUDGE"] = np.select(
    [cap["N"] < MIN_N, cap["Cpk"] >= 1.33, cap["Cpk"] >= 1.0],
    ["표본부족", "양호", "관리필요"],
    default="개선필요",
)
cap[["MEAN", "STD_ALL", "SIGMA_HAT", "Cp", "Cpk", "Pp", "Ppk"]] = cap[
    ["MEAN", "STD_ALL", "SIGMA_HAT", "Cp", "Cpk", "Pp", "Ppk"]
].round(4)

violations = df.loc[
    df["RULE_VIOLATED"], GROUP + ["MEAS_TIME", "LOT_ID", "WAFER_NO", VALUE, "CL", "UCL", "LCL", "SIGMA_Z", "RULE_NAMES"]
]
if violations.empty:
    violations = df.head(1)[GROUP + ["MEAS_TIME", "LOT_ID", "WAFER_NO", VALUE, "CL", "UCL", "LCL", "SIGMA_Z"]].assign(
        RULE_NAMES="NO_VIOLATION"
    )

output = df.drop(columns=[c for c in df.columns if c.startswith("_")]).reset_index(drop=True)
output_capability = cap.sort_values("Cpk").reset_index(drop=True)
output_violation = violations.reset_index(drop=True)
```

## 핵심 포인트

- **σ 추정 방식이 두 가지**라는 게 SPC의 핵심입니다.
  - **군내 변동** σ̂ = MR̄/1.128 → 관리한계선과 **Cp/Cpk** 에 사용 (설비 자체의 능력)
  - **전체 표준편차** → **Pp/Ppk** 에 사용 (실제 산포 성능)
  - 둘의 차이가 크면 **시간에 따른 드리프트나 층별 요인**이 있다는 신호입니다.
- Western Electric 룰 구현 패턴을 기억해 두세요. 응용 범위가 아주 넓습니다.
  - **"연속 N점 같은 쪽"** → `(sign == sign).rolling(N).sum() == N`
  - **"연속 N점 중 M점"** → `flag.rolling(N).sum() >= M`
  - **"연속 상승/하강"** → `diff > 0` 을 `rolling(N-1).sum()` 으로 세기
- Cpk 판정 기준(일반적으로 통용되는 값): 1.33 이상 양호, 1.0~1.33 관리 필요, 1.0 미만 개선 필요.
- 표본이 너무 적은 그룹(여기서는 30개 미만)은 **계산하지 말고 제외**하세요.
  표본 5개짜리 Cpk는 숫자는 나오지만 아무 의미가 없습니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수를 작성해줘. SPC 관리도를 만들 거야.
입력: input(DataFrame), sigma_k(float, 기본 3.0)
컬럼: EQP_ID, STEP_DESC, MEAS_TIME(문자열), THICKNESS
규격(공정별 중심값, 허용 편차율): PC 520±3%, RMG 310±3%, CBCMP 980±2%, ETCH 145±5%, PHOTO 88±5%

1. (EQP_ID, STEP_DESC) 그룹별로 개별값 관리도(I chart)를 만들어줘.
   - CL = 그룹 평균
   - sigma_hat = 이동범위 평균 / 1.128  (군내 변동 추정)
   - UCL/LCL = CL ± sigma_k * sigma_hat
2. Western Electric 룰 1,2,3,5를 구현해서 위반 여부 컬럼을 각각 만들어줘.
   (Rule1: 1점이 3시그마 밖 / Rule2: 연속 9점 중심선 한쪽 /
    Rule3: 연속 6점 연속 상승 또는 하강 / Rule5: 연속 3점 중 2점이 같은 쪽 2시그마 밖)
3. 그룹별 Cp, Cpk(군내 sigma 사용), Pp, Ppk(전체 표준편차 사용)를 계산해서 별도 테이블로.
   표본 30개 미만 그룹은 계산하지 말고 JUDGE='표본부족' 으로 표시.
4. 룰 위반 지점만 모은 테이블도 별도로.
groupby + transform + rolling 으로 벡터화해서 작성하고, apply(axis=1) 은 쓰지 마.
0으로 나누는 경우를 방어하고, 출력은 output / output_capability / output_violation.
```

> **룰 정의를 프롬프트에 직접 써 준 것**에 주목하세요. "Western Electric 룰 구현해줘"만 하면
> AI마다 룰 번호 해석이 조금씩 다릅니다. **판정 기준을 문장으로 명시**하면 검증 가능한 코드가 나옵니다.

## 확인 & 응용

- `output` 으로 라인 차트 + CL/UCL/LCL 기준선을 그리고, `RULE_VIOLATED` 로 점 색상을 칠하세요.
- `output_capability` 를 `JUDGE` 로 정렬하면 개선 우선순위 목록이 그대로 나옵니다.
- **응용**: 부분군(랏 단위) X̄-R 관리도로 바꿔 보세요. 부분군 크기 n=25일 때 `d2=3.931` 을 씁니다.
- **응용**: `sigma_k` 를 2.0으로 낮춰 사전 경보용 관리도를 따로 만들어 보세요.

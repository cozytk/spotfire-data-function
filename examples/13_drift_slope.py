'''---
title: 설비별 드리프트 기울기와 규격 도달 예상 시점
level: 3
difficulty: ★★★
summary: 그룹마다 회귀선을 적합해 기울기·R²를 데이터로 뽑고, 현재 추세라면 언제 규격을 벗어나는지 예측합니다.
data: [fab_measurement.csv]
inputs:
  input:
    file: fab_measurement.csv
outputs: [output, output_forecast]
---
## 시나리오

"어느 설비가 얼마나 빠르게 드리프트하고 있는가?"
그리고 "이대로면 며칠 뒤에 규격을 벗어나는가?"

이 두 질문에 답하면 **사후 대응이 사전 예방으로 바뀝니다.** PM(예방보전) 우선순위가 여기서 나옵니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire 산점도에 **추세선을 그릴 수는** 있습니다. 눈으로 보는 것까지는 됩니다.
- 하지만 그 **기울기 값을 데이터로 꺼낼 수 없습니다.** 설비가 20대면 추세선 20개를 눈으로 비교해야 합니다.
- "기울기 순으로 정렬한 설비 랭킹", "규격 도달 예상일" 같은 **파생 데이터**는 만들 수 없습니다.
- 데이터 함수는 그룹마다 회귀를 돌려 **기울기를 하나의 테이블로** 만들어 줍니다. 정렬·필터·알람 연동이 모두 가능해집니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 출력 | `output` | Table | 그룹별 기울기/절편/R² 랭킹 |
| 출력 | `output_forecast` | Table | 규격 도달 예상 시점 |

## 스크립트

{{CODE}}

## 핵심 포인트

- `np.polyfit(x, y, 1)` 이 1차 회귀의 가장 단순한 형태입니다. 반환값은 `[기울기, 절편]`.
  scikit-learn을 설치할 필요가 전혀 없습니다. **numpy만으로 충분**합니다.
- **X축 단위를 반드시 의미 있는 단위로 바꾸세요.** 시각을 그대로 넣으면 나노초 단위 기울기가 나옵니다.
  여기서는 "시작 시점부터 경과 일수"로 바꿔 **일당 변화량(Å/day)** 을 만들었습니다. 현업이 바로 이해하는 단위입니다.
- 그룹마다 계산해야 할 때는 **`for ... in df.groupby(...)` 루프가 가장 읽기 쉽습니다.**
  그룹 수가 수백 개 이하면 성능도 충분합니다. 모든 걸 벡터화하려 애쓰지 마세요.
- **R²를 함께 내보내세요.** R²가 낮으면 기울기는 의미가 없습니다. 이 검증 없이 기울기만 보고
  설비를 세우면 오경보가 됩니다.
- 예측은 **선형 추세가 유지된다는 가정**이며, 반드시 그 사실을 컬럼이나 문서로 남기세요.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input(DataFrame).
컬럼: EQP_ID, STEP_DESC, MEAS_TIME(문자열 시각), THICKNESS
공정 규격: PC 520±3%, RMG 310±3%, CBCMP 980±2%, ETCH 145±5%, PHOTO 88±5%

1. (EQP_ID, STEP_DESC) 그룹별로 THICKNESS 를 '경과 일수'에 대해 1차 회귀(np.polyfit)
   - X는 그룹 내 최초 측정 시각 기준 경과 일수(float)
   - 출력: SLOPE_PER_DAY, INTERCEPT, R2, N, 기간(DAYS)
2. 표본 30개 미만이거나 기간이 1일 미만인 그룹은 제외
3. |기울기| 기준 내림차순 정렬하고 DRIFT_RANK 부여
4. 각 그룹에 대해 현재 추세가 유지될 때 USL 또는 LSL 에 도달하는 예상 일수와 예상 날짜 계산
   - R2 < 0.3 이면 신뢰할 수 없으므로 예측하지 말고 '추세없음' 으로 표기
   - 이미 규격을 벗어났으면 '규격이탈' 로 표기
5. 결과는 output(기울기 랭킹), output_forecast(예측)
sklearn 은 쓰지 말고 numpy 로만 계산해줘. 0으로 나누는 경우를 방어해줘.
```

## 확인 & 응용

- `output` 을 `DRIFT_RANK` 순으로 표시하면 그대로 PM 우선순위 목록입니다.
- **응용**: 최근 7일 데이터만 잘라 기울기를 다시 계산하고 전체 기간 기울기와 비교해 보세요.
  **최근 기울기가 급해졌다면** 상태 변화가 시작된 것입니다.
- **응용**: `STEP_DESC` 대신 `CHAMBER` 를 그룹에 넣어 챔버별 편차를 보세요.
'''
import numpy as np
import pandas as pd

df = input.copy()
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])
df = df.dropna(subset=["THICKNESS"])

GROUP = ["EQP_ID", "STEP_DESC"]
MIN_N = 30
SPEC = {"PC": (520.0, 0.03), "RMG": (310.0, 0.03), "CBCMP": (980.0, 0.02),
        "ETCH": (145.0, 0.05), "PHOTO": (88.0, 0.05)}

rows = []
for (eqp, step), block in df.groupby(GROUP):
    block = block.sort_values("MEAS_TIME")
    if len(block) < MIN_N:
        continue
    t0 = block["MEAS_TIME"].iloc[0]
    # X축을 '경과 일수'로 : 기울기가 Å/day 라는 이해 가능한 단위가 된다
    x = (block["MEAS_TIME"] - t0).dt.total_seconds().to_numpy() / 86400.0
    y = block["THICKNESS"].to_numpy()
    if x.max() - x.min() < 1.0:
        continue

    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    ss_res = float(((y - y_hat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    center, tol = SPEC.get(step, (np.nan, np.nan))
    rows.append(
        {
            "EQP_ID": eqp, "STEP_DESC": step, "N": len(block),
            "T_START": t0, "T_END": block["MEAS_TIME"].iloc[-1], "DAYS": round(float(x.max()), 2),
            "SLOPE_PER_DAY": round(float(slope), 4), "INTERCEPT": round(float(intercept), 3),
            "R2": round(float(r2), 4),
            "LAST_VALUE": round(float(y[-1]), 3),
            "USL": center * (1 + tol), "LSL": center * (1 - tol),
        }
    )

res = pd.DataFrame(rows)
res["ABS_SLOPE"] = res["SLOPE_PER_DAY"].abs()
res = res.sort_values("ABS_SLOPE", ascending=False).reset_index(drop=True)
res["DRIFT_RANK"] = np.arange(1, len(res) + 1)

# --- 규격 도달 예상 시점 ----------------------------------------------------
fc = res.copy()
slope_safe = fc["SLOPE_PER_DAY"].replace(0, np.nan)
target = np.where(fc["SLOPE_PER_DAY"] > 0, fc["USL"], fc["LSL"])
days_to_spec = (target - fc["LAST_VALUE"]) / slope_safe

fc["TARGET_LIMIT"] = np.round(target, 3)
fc["DAYS_TO_SPEC"] = np.round(days_to_spec, 1)
fc["STATUS"] = np.select(
    [
        (fc["LAST_VALUE"] > fc["USL"]) | (fc["LAST_VALUE"] < fc["LSL"]),
        fc["R2"] < 0.3,
        fc["DAYS_TO_SPEC"] <= 0,
        fc["DAYS_TO_SPEC"] <= 30,
    ],
    ["규격이탈", "추세없음", "규격이탈", "30일내 도달"],
    default="여유",
)
fc["EXPECTED_DATE"] = fc["T_END"] + pd.to_timedelta(fc["DAYS_TO_SPEC"].clip(lower=0).fillna(0), unit="D")
fc.loc[fc["STATUS"].isin(["추세없음", "규격이탈"]), ["DAYS_TO_SPEC", "EXPECTED_DATE"]] = [np.nan, pd.NaT]

# 전부 결측인 컬럼이 생기면 Spotfire 출력이 실패하므로 방어
if fc["EXPECTED_DATE"].isna().all():
    fc["EXPECTED_DATE"] = fc["T_END"]
if fc["DAYS_TO_SPEC"].isna().all():
    fc["DAYS_TO_SPEC"] = 0.0

output = res
output_forecast = fc[
    ["EQP_ID", "STEP_DESC", "N", "SLOPE_PER_DAY", "R2", "LAST_VALUE", "USL", "LSL",
     "TARGET_LIMIT", "DAYS_TO_SPEC", "EXPECTED_DATE", "STATUS"]
]

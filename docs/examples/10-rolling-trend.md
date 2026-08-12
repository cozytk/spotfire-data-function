---
title: "10. 이동평균·이동표준편차·EWMA로 트렌드 잡기"
parent: 예제 모음
nav_order: 10
---

# 10. 이동평균·이동표준편차·EWMA로 트렌드 잡기
{: .no_toc }

**난이도** ★★☆ · **Level 3 · 시계열과 공정 분석**

설비별로 최근 N장 이동 통계를 계산해 노이즈를 걷어내고, 단기 평균이 장기 평균을 이탈하는 시점을 잡아냅니다.

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/10_rolling_trend.py)

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
| 입력 | `window` | Value | 문서 속성 (예: `25`) |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_alert` | Table | 새 데이터 테이블 |

---

## 시나리오

웨이퍼 한 장 한 장의 두께는 노이즈가 큽니다. "최근 25장(=1랏) 이동평균"으로 보면 설비 상태 변화가 드러납니다.
여기에 **단기 이동평균(25) vs 장기 이동평균(100)** 을 비교하면 드리프트 시작 시점을 잡을 수 있습니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire에 이동평균 표현식(`Avg([X]) OVER (LastPeriods(25,[Time]))`)이 있긴 합니다. 다만
  - **정렬 축과 그룹(설비)** 을 동시에 다루면 표현식이 급격히 어려워지고,
  - **이동 표준편차·EWMA·이동 중앙값**은 사실상 지원되지 않으며,
  - 여러 윈도우를 비교하려면 표현식을 윈도우 개수만큼 복제해야 합니다.
- pandas의 `rolling` / `ewm` 은 이 전부를 한 줄씩으로 처리합니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 입력 | `window` | Value (Integer) | 문서 속성 `Window` (기본 25 = 1랏) |
| 출력 | `output` | Table | 이동 통계가 붙은 원본 |
| 출력 | `output_alert` | Table | 골든크로스/데드크로스 발생 지점 |

## 스크립트

```python
import numpy as np
import pandas as pd

df = input.copy()
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])

GROUP = ["EQP_ID", "STEP_DESC"]
w = int(window)
w_long = w * 4
min_p = max(2, w // 2)

# rolling 계산의 전제 : 그룹 내 시간 정렬
df = df.sort_values(GROUP + ["MEAS_TIME"]).reset_index(drop=True)
g = df.groupby(GROUP)["THICKNESS"]

df["MA_SHORT"] = g.transform(lambda s: s.rolling(w, min_periods=min_p).mean())
df["MA_LONG"] = g.transform(lambda s: s.rolling(w_long, min_periods=min_p).mean())
df["STD_SHORT"] = g.transform(lambda s: s.rolling(w, min_periods=min_p).std())
df["EWMA"] = g.transform(lambda s: s.ewm(span=w, adjust=False).mean())

df["BAND_UP"] = df["MA_LONG"] + 2 * df["STD_SHORT"]
df["BAND_LO"] = df["MA_LONG"] - 2 * df["STD_SHORT"]
df["OUT_OF_BAND"] = (df["THICKNESS"] > df["BAND_UP"]) | (df["THICKNESS"] < df["BAND_LO"])

# 단기/장기 이동평균 교차 지점 탐지
# groupby().shift() 를 쓰면 그룹의 첫 행은 NaN 이 되어 '가짜 교차'가 잡히지 않는다
df["MA_DIFF"] = df["MA_SHORT"] - df["MA_LONG"]
prev_diff = df.groupby(GROUP)["MA_DIFF"].shift()

df["CROSS"] = np.select(
    [(prev_diff <= 0) & (df["MA_DIFF"] > 0), (prev_diff >= 0) & (df["MA_DIFF"] < 0)],
    ["GOLDEN", "DEAD"],
    default="",
)

alerts = df[df["CROSS"] != ""][GROUP + ["MEAS_TIME", "THICKNESS", "MA_SHORT", "MA_LONG", "CROSS"]]

if alerts.empty:
    alerts = pd.DataFrame(
        [{"EQP_ID": "NONE", "STEP_DESC": "NONE", "MEAS_TIME": df["MEAS_TIME"].min(),
          "THICKNESS": 0.0, "MA_SHORT": 0.0, "MA_LONG": 0.0, "CROSS": "NO_CROSS"}]
    )

num = ["MA_SHORT", "MA_LONG", "STD_SHORT", "EWMA", "BAND_UP", "BAND_LO"]
df[num] = df[num].round(3)

output = df.sort_values("MEAS_TIME").reset_index(drop=True)
output_alert = alerts.reset_index(drop=True)
```

## 핵심 포인트

- **`rolling` 전에 반드시 정렬**하세요. 시간순 정렬 없이 계산한 이동평균은 아무 의미가 없습니다.
  이것이 이동 통계에서 가장 흔한 실수입니다.
- 그룹별 이동 통계는 `df.groupby(키)[값].transform(lambda s: s.rolling(w).mean())` 형태가 안전합니다.
  `transform` 을 쓰면 결과가 **원본 행에 그대로 정렬**되어 붙습니다.
- `min_periods` 를 지정하지 않으면 앞쪽 `window-1` 개 행이 전부 `NaN` 이 됩니다.
  그룹이 작을 때 **컬럼 전체가 결측**이 되어 Spotfire 출력 오류로 이어질 수 있습니다.
- `ewm(span=n)` 은 최근 값에 가중치를 더 주는 지수가중이동평균입니다. 반응이 빠른 대신 노이즈에 민감합니다.
- **크로스 시점**은 `(현재 부호 != 직전 부호)` 로 잡습니다. 시계열 이벤트 탐지의 기본 패턴입니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input(DataFrame), window(int, 기본 25).
컬럼: EQP_ID, STEP_DESC, MEAS_TIME(문자열), THICKNESS
1. (EQP_ID, STEP_DESC) 그룹 안에서 MEAS_TIME 순으로 정렬
2. 아래 이동 통계 컬럼 추가 (groupby + transform + rolling 사용, min_periods 는 window의 절반)
   - MA_SHORT(window), MA_LONG(window*4), STD_SHORT(window), EWMA(span=window)
   - BAND_UP = MA_LONG + 2*STD_SHORT, BAND_LO = MA_LONG - 2*STD_SHORT
3. MA_SHORT 가 MA_LONG 을 상향/하향 돌파하는 지점에 CROSS 컬럼('GOLDEN'/'DEAD'/'') 표시
4. CROSS 가 발생한 행만 모아 output_alert 로 별도 출력 (비면 안내용 1행 생성)
출력: output, output_alert
```

## 확인 & 응용

- 라인 차트에 `THICKNESS`(점), `MA_SHORT`, `MA_LONG`, 밴드 2개를 함께 그리면 그대로 트렌드 모니터가 됩니다.
- **응용**: `rolling(...).median()` 으로 바꾸면 스파이크에 둔감한 이동 중앙값이 됩니다.
- **응용**: `window` 를 시간 기반(`rolling("6h", on="MEAS_TIME")`)으로 바꿔 보세요.
  계측 간격이 불규칙할 때는 개수 기반보다 시간 기반이 정확합니다.

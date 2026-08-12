---
title: "15. 연속 이벤트를 하나의 "세션"으로 묶기"
parent: 예제 모음
nav_order: 15
---

# 15. 연속 이벤트를 하나의 "세션"으로 묶기
{: .no_toc }

**난이도** ★★★ · **Level 3 · 시계열과 공정 분석**

30분 이상 끊기면 새 세션. 흩어진 알람 로그를 사건 단위로 묶어 지속시간·건수·대표 원인을 만들어 냅니다.

사용 데이터: [`equipment_alarm_log.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/equipment_alarm_log.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/15_event_sessionize.py)

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

### 파라미터 요약
{: .no_toc }

| 구분 | 이름 | 타입 | 연결 |
|---|---|---|---|
| 입력 | `input` | Table | `equipment_alarm_log.csv` |
| 입력 | `gap_minutes` | Value | 문서 속성 (예: `30`) |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_session` | Table | 새 데이터 테이블 |

---

## 시나리오

알람 로그는 한 번의 설비 이상에 대해 **수십 건이 연속으로** 쏟아집니다.
"알람 900건"이라는 숫자는 의미가 없습니다. 알고 싶은 건 **"사건이 몇 번 있었고, 각각 얼마나 오래 갔는가"** 입니다.

규칙: **같은 설비에서 30분 이내에 이어지는 알람은 하나의 사건(세션)으로 본다.**

## 왜 Spotfire 기본 기능으로는 어려운가

- 이건 **"이전 행과 비교"** 가 필요한 작업입니다. Spotfire 표현식은 기본적으로 **행 단위**로 동작합니다.
- `Previous()` 유사 기능을 OVER 표현식으로 흉내 낼 수는 있지만,
  **"그 판정을 누적해서 그룹 번호를 매기는 것"** 은 불가능합니다. 누적 로직이 필요하기 때문입니다.
- 데이터 함수에서는 **`shift()` + `cumsum()`** 두 함수면 끝납니다.
  이 패턴은 세션화·연속 불량·연속 가동/정지 등 **아주 많은 곳에 재사용**됩니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `equipment_alarm_log` |
| 입력 | `gap_minutes` | Value (Integer) | 문서 속성 `GapMinutes` (기본 30) |
| 출력 | `output` | Table | 원본 + 세션 ID |
| 출력 | `output_session` | Table | 세션 단위 요약 |

## 스크립트

```python
import numpy as np
import pandas as pd

df = input.copy()
df["ALARM_TIME"] = pd.to_datetime(df["ALARM_TIME"])

# 1) 정렬 — 세션화의 전제
df = df.sort_values(["EQP_ID", "ALARM_TIME"]).reset_index(drop=True)

# 2) 직전 알람과의 간격이 기준을 넘으면 '새 세션 시작'
gap = df.groupby("EQP_ID")["ALARM_TIME"].diff()
is_new_session = gap > pd.Timedelta(minutes=int(gap_minutes))

# 3) 누적합 = 세션 번호 (설비별로 따로 센다)
df["SESSION_NO"] = is_new_session.groupby(df["EQP_ID"]).cumsum().astype(int)
df["SESSION_ID"] = df["EQP_ID"] + "_S" + df["SESSION_NO"].astype(str).str.zfill(3)
df["GAP_MIN"] = (gap.dt.total_seconds() / 60).round(2)

# 4) 세션 단위 요약
sess = (
    df.groupby(["EQP_ID", "SESSION_ID"], as_index=False)
    .agg(
        START=("ALARM_TIME", "min"),
        END=("ALARM_TIME", "max"),
        ALARM_CNT=("ALARM_TIME", "size"),
        ERROR_CNT=("SEVERITY", lambda s: int((s == "ERROR").sum())),
        WARN_CNT=("SEVERITY", lambda s: int((s == "WARN").sum())),
        TOP_MESSAGE=("MESSAGE", lambda s: s.mode().iloc[0] if not s.mode().empty else ""),
        RECIPES=("RECIPE", lambda s: ", ".join(sorted(set(s))[:3])),
    )
)
sess["DURATION_MIN"] = ((sess["END"] - sess["START"]).dt.total_seconds() / 60).round(1)
sess["MAX_SEVERITY"] = np.select(
    [sess["ERROR_CNT"] > 0, sess["WARN_CNT"] > 0], ["ERROR", "WARN"], default="INFO"
)
sess["IS_MAJOR"] = (sess["DURATION_MIN"] >= 30) | (sess["ERROR_CNT"] >= 5)

output = df
output_session = sess.sort_values("DURATION_MIN", ascending=False).reset_index(drop=True)
```

## 핵심 포인트

**꼭 외워 두면 좋은 3줄 패턴입니다.**

```python
df = df.sort_values(["KEY", "TIME"])                       # 1. 정렬
is_new = df.groupby("KEY")["TIME"].diff() > 기준           # 2. '새 세션 시작?' 판정
df["SESSION_ID"] = is_new.groupby(df["KEY"]).cumsum()      # 3. 누적합 = 그룹 번호
```

- `cumsum()` 이 핵심입니다. `True` 를 1로 세면서 누적하면 **끊길 때마다 번호가 1씩 증가**합니다.
- 그룹(설비)의 첫 행은 `diff()` 가 `NaT` → 비교가 `False` 라 자동으로 세션 0이 됩니다.
- 같은 패턴으로 **"값이 바뀔 때마다"** 새 그룹을 만들 수도 있습니다:
  `(df["STATE"] != df["STATE"].shift()).cumsum()` — 연속 불량 웨이퍼 구간 탐지에 그대로 씁니다.
- 세션 요약에서 `agg` 에 여러 함수를 넘길 때 **`("컬럼","함수")` 튜플 형식**을 쓰면 결과 컬럼명이 깔끔해집니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input(알람로그), gap_minutes(int).
컬럼: EQP_ID, ALARM_TIME(문자열 시각), SEVERITY(INFO/WARN/ERROR), MESSAGE, RECIPE

같은 EQP_ID 안에서 직전 알람과의 간격이 gap_minutes 분을 넘으면 새로운 세션으로 간주해줘.
1. 각 행에 SESSION_ID (EQP_ID + 순번 형태의 문자열) 부여
2. 세션별 요약: 시작/종료 시각, 지속시간(분), 알람 건수, ERROR/WARN 건수,
   가장 많이 나온 메시지, 관련 설비, 심각도 최고 등급
3. 지속시간 30분 이상이거나 ERROR 5건 이상인 세션은 IS_MAJOR=True 로 표시
4. 세션 요약을 지속시간 내림차순 정렬
shift/diff/cumsum 을 사용하고 for 루프는 쓰지 마. 출력은 output, output_session.
```

## 확인 & 응용

- `output_session` 을 지속시간 순으로 보면 **그날의 진짜 사건 Top 10** 이 됩니다.
- **응용**: `wafer_yield.csv` 에서 웨이퍼 번호 순으로 "수율 90% 미만이 연속된 구간"을 찾아보세요.
  똑같은 패턴으로 풀립니다.
- **응용**: 세션 요약을 [14번 예제](../14-merge-asof/)로 계측 데이터에 붙이면
  "알람 세션 중에 측정된 웨이퍼"를 표시할 수 있습니다.

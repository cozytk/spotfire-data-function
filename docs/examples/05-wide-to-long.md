---
title: 05. Wide → Long 변환 (센서 200개 컬럼을 3개로)
parent: 예제 모음
nav_order: 5
---

# 05. Wide → Long 변환 (센서 200개 컬럼을 3개로)
{: .no_toc }

**난이도** ★★☆ · **Level 2 · 재구조화**

melt 한 줄로 컬럼이 곧 데이터인 형태를 정규화합니다. 컬럼이 수십~수백 개일 때 Spotfire 기본 기능으로는 사실상 불가능한 작업.

사용 데이터: [`equipment_sensor_wide.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/equipment_sensor_wide.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/05_wide_to_long.py)

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

### 파라미터 요약
{: .no_toc }

| 구분 | 이름 | 타입 | 연결 |
|---|---|---|---|
| 입력 | `input` | Table | `equipment_sensor_wide.csv` |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_summary` | Table | 새 데이터 테이블 |

---

## 시나리오

설비에서 내려온 센서 데이터가 이런 모양입니다.

| TIMESTAMP | EQP_ID | S001 | S002 | ... | S020 |
|---|---|---|---|---|---|
| 2026-03-02 06:00 | ETC01 | 48.2 | 51.7 | ... | 55.1 |

센서가 20개면 그럭저럭이지만 실제로는 **200~2,000개**입니다.
이 상태로는 "센서별 트렌드를 한 화면에 색으로 구분해서" 볼 수 없습니다.
Spotfire 시각화는 **Long 포맷**(한 행 = 한 관측)일 때 가장 강력합니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire에 **Unpivot(피벗 해제) 데이터 변환**이 있긴 합니다. 하지만
  - 대상 컬럼을 **하나하나 클릭해서 선택**해야 하고,
  - 센서가 추가/삭제될 때마다 변환 설정을 다시 만져야 하며,
  - 소스가 바뀌면 조용히 깨집니다.
- 데이터 함수는 `id_vars` 만 지정하면 **나머지 전부**를 자동으로 잡습니다. 컬럼이 2,000개여도 코드는 같습니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `equipment_sensor_wide` |
| 출력 | `output` | Table | Long 포맷 센서 데이터 |
| 출력 | `output_summary` | Table | 센서별 요약 통계 |

## 스크립트

```python
import pandas as pd

df = input.copy()

ID_COLS = ["TIMESTAMP", "EQP_ID"]
# 키 컬럼을 뺀 나머지를 '센서 컬럼'으로 자동 인식 — 센서가 몇 개든 코드는 동일
sensor_cols = [c for c in df.columns if c not in ID_COLS]

long_df = df.melt(
    id_vars=ID_COLS,
    value_vars=sensor_cols,
    var_name="SENSOR",
    value_name="VALUE",
)

# 결측(통신 유실) 행 제거
long_df = long_df.dropna(subset=["VALUE"])

# 센서 이름에서 번호만 추출 (S007 -> 7)
long_df["SENSOR_NO"] = long_df["SENSOR"].str.extract(r"(\d+)").astype(int)
long_df["TIMESTAMP"] = pd.to_datetime(long_df["TIMESTAMP"])

# 센서별 요약 : 평균/표준편차/결측률
total_per_sensor = len(df)
summary = (
    long_df.groupby(["EQP_ID", "SENSOR"], as_index=False)
    .agg(N=("VALUE", "size"), MEAN=("VALUE", "mean"), STD=("VALUE", "std"), MIN=("VALUE", "min"), MAX=("VALUE", "max"))
)
summary["MISSING_PCT"] = (1 - summary["N"] / (total_per_sensor / df["EQP_ID"].nunique())) * 100
summary[["MEAN", "STD", "MIN", "MAX", "MISSING_PCT"]] = summary[["MEAN", "STD", "MIN", "MAX", "MISSING_PCT"]].round(3)

output = long_df.sort_values(["EQP_ID", "TIMESTAMP", "SENSOR_NO"]).reset_index(drop=True)
output_summary = summary
```

## 핵심 포인트

- `id_vars` = **유지할 키 컬럼**, `value_vars` = 녹여 없앨 컬럼. `value_vars` 를 생략하면 나머지 전부입니다.
- 여기서는 `ID_COLS` 만 정의하고 **나머지를 자동 탐지**했습니다. 이것이 컬럼 개수에 무관해지는 비결입니다.
- Long 변환 후 행 수는 `원본 행 × 센서 수` 로 폭증합니다.
  1,344행 × 20센서 = 26,880행. 센서가 500개면 67만 행이 됩니다.
  **필요 없는 센서는 melt 전에 걸러내는 것**이 성능의 핵심입니다.
- 센서 이름에서 그룹/번호를 뽑아내려면 `str.extract(r"S(\d+)")` 같은 정규식을 씁니다 ([16번 예제](../16-regex-parse-log/)).

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수를 작성해줘.
입력 input 은 wide 포맷 센서 데이터야. 키 컬럼은 TIMESTAMP, EQP_ID 이고
나머지 컬럼은 전부 센서값(컬럼명 S001, S002 ...)이야. 센서 개수는 그때그때 달라질 수 있어.
1. 키 컬럼을 제외한 나머지를 자동으로 찾아 long 포맷(TIMESTAMP, EQP_ID, SENSOR, VALUE)으로 변환
2. 값이 결측인 행은 제외
3. 센서 이름에서 숫자만 뽑아 SENSOR_NO(정수) 컬럼 추가
4. 센서별 평균/표준편차/결측률 요약 테이블도 별도로 출력
컬럼명을 하드코딩하지 말 것. 출력은 output, output_summary.
```

> **"컬럼명을 하드코딩하지 말 것"** — 이 한 줄이 없으면 AI는 `value_vars=['S001','S002',...]` 처럼
> 전부 나열한 코드를 주기 쉽습니다. 재사용 가능한 코드를 얻으려면 꼭 넣으세요.

## 확인 & 응용

- 변환 후 `SENSOR` 를 색상, `TIMESTAMP` 를 X축으로 놓은 라인 차트를 만들어 보세요.
- **응용**: 반대 방향(Long → Wide)은 [06번 예제](../06-pivot-crosstab/)의 `pivot_table` 입니다.

'''---
title: 중복 행 제거와 "키 기준 최신값만 남기기"
level: 1
difficulty: ★☆☆
summary: Spotfire에 아예 없는 기능 1순위. 완전 중복 제거에서 시작해, 같은 키의 재측정 이력 중 최신 1건만 남기는 데까지 확장합니다.
data: [fab_measurement.csv]
inputs:
  input:
    file: fab_measurement.csv
outputs: [output, output_removed]
---
## 시나리오

MES에서 내려받은 계측 이력에는 두 종류의 "중복"이 섞여 있습니다.

1. **완전 중복** — 수집 시스템이 같은 레코드를 재전송해서 모든 컬럼이 똑같은 행
2. **재측정** — 같은 `LOT_ID + WAFER_NO + STEP_DESC`인데 `MEAS_TIME`과 측정값만 다른 행

1번은 지워야 하고, 2번은 **가장 최근 측정값 1건만** 남겨야 정확한 수율/트렌드가 나옵니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire에는 **"중복 행 제거" 메뉴가 없습니다.** 가장 흔하게 겪는 결핍입니다.
- 흔한 우회법은 `LOT_ID & "|" & WAFER_NO` 로 키 컬럼을 만들고 `Rank()`/`Max()` 계산 컬럼을 얹은 뒤
  `Rank(...)=1` 로 필터링하는 것인데, 계산 컬럼 3~4개 + 필터가 필요하고
  **행이 실제로 지워지는 게 아니라 숨겨질 뿐**이라 이후 집계에서 계속 신경 써야 합니다.
- 데이터 함수는 이 작업을 **두 줄**로 끝내고, 결과가 "행이 실제로 제거된 새 데이터 테이블"입니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` 데이터 테이블 |
| 출력 | `output` | Table | 새 데이터 테이블 `fab_dedup` |
| 출력 | `output_removed` | Table | 새 데이터 테이블 `fab_dedup_removed` (검증용) |

> 출력 테이블을 2개 만들어 "무엇이 지워졌는지"를 함께 보여 주면 현업 검증이 훨씬 빨라집니다.
> 데이터 함수는 출력 개수에 제한이 없습니다.

## 스크립트

{{CODE}}

## 핵심 포인트

- `drop_duplicates()` 는 **인자 없이 쓰면 모든 컬럼이 같은 행**을 제거합니다.
- `subset=[...]` 로 "같다고 볼 기준 컬럼"을 지정하고, `keep="last"` 로 마지막 행을 남깁니다.
  이때 **정렬이 먼저**입니다. `sort_values()` 없이 `keep="last"` 를 쓰면 파일에 담긴 순서에 의존하게 됩니다.
- `~mask` 로 제거된 행만 따로 뽑아 두 번째 출력으로 내보내면, 결과를 신뢰할 수 있는지 바로 확인됩니다.
- `reset_index(drop=True)` 는 습관적으로 붙이세요. Spotfire로 나갈 때 인덱스는 버려지지만,
  이어지는 pandas 연산에서 인덱스가 어긋나 생기는 사고를 막아 줍니다.

## 이렇게 물어보세요 (프롬프트)

```text
너는 Spotfire Python 데이터 함수를 작성한다.
입력: input (pandas DataFrame). 컬럼은 LOT_ID, WAFER_NO, STEP_DESC, MEAS_TIME(문자열 'YYYY-MM-DD HH:MM:SS'), THICKNESS, CD ...
요구사항:
1. 모든 컬럼이 동일한 완전 중복 행을 제거한다.
2. LOT_ID, WAFER_NO, STEP_DESC 가 같으면 재측정으로 보고 MEAS_TIME 이 가장 늦은 1건만 남긴다.
3. 제거된 행은 output_removed 로 따로 내보낸다.
제약:
- 최종 결과는 반드시 output, output_removed 변수에 DataFrame 으로 할당한다.
- import 는 스크립트 안에 포함한다. 파일 입출력·print 는 사용하지 않는다.
- inplace=True 는 쓰지 않는다.
```

## 확인 & 응용

- `output` 행 수 + `output_removed` 행 수 = 원본 행 수 인지 확인하세요.
- **응용 1**: `keep="first"` 로 바꿔 "최초 측정값" 기준 테이블도 만들어 비교해 보세요.
- **응용 2**: 재측정이 2회 이상 발생한 웨이퍼만 뽑아 "재측정 다발 설비" 목록을 만들어 보세요.
  (힌트: `df.groupby(keys).size()` 가 2 이상인 것)
'''
import pandas as pd

df = input.copy()
df["MEAS_TIME"] = pd.to_datetime(df["MEAS_TIME"])

# 1) 완전 중복 제거 : 모든 컬럼이 동일한 행
df_step1 = df.drop_duplicates()

# 2) 재측정 정리 : 같은 (LOT, WAFER, STEP) 중 MEAS_TIME 이 가장 늦은 1건만 남김
KEYS = ["LOT_ID", "WAFER_NO", "STEP_DESC"]
df_step1 = df_step1.sort_values(KEYS + ["MEAS_TIME"])
kept = df_step1[~df_step1.duplicated(subset=KEYS, keep="last")]

# 3) 무엇이 지워졌는지 = 원본에서 살아남지 못한 행 (완전중복 + 옛 재측정)
removed = df[~df.index.isin(kept.index)]

output = kept.sort_values("MEAS_TIME").reset_index(drop=True)
output_removed = removed.sort_values("MEAS_TIME").reset_index(drop=True)

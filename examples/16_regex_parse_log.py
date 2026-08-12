'''---
title: 정규식으로 로그 메시지에서 구조화된 컬럼 뽑아내기
level: 3
difficulty: ★★★
summary: 한 덩어리 텍스트에 갇혀 있는 알람 코드·LOT·수치를 컬럼으로 꺼내 분석 가능한 데이터로 바꿉니다.
data: [equipment_alarm_log.csv]
inputs:
  input:
    file: equipment_alarm_log.csv
outputs: [output, output_by_code]
---
## 시나리오

알람 로그의 `MESSAGE` 컬럼이 이렇게 생겼습니다.

```text
[E-1023] Chamber pressure high (LOT=L26043, STEP=ETCH, value=12.34 unit)
```

여기서 알람코드, 설명, LOT, STEP, 수치를 **각각의 컬럼으로** 꺼내야
"알람코드별 발생 추이", "LOT별 알람 이력" 같은 분석이 가능해집니다.

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire 계산 컬럼에 `Find()`, `Substring()` 은 있지만 **정규식 캡처 그룹이 없습니다.**
- 5개 항목을 뽑으려면 `Substring(...Find(...)+1, Find(...)-Find(...)-1)` 같은 표현식을 **5번** 써야 하고,
  메시지 포맷이 조금만 달라져도 전부 깨집니다.
- pandas의 `str.extract()` 는 **정규식 하나로 여러 컬럼을 한 번에** 만들어 냅니다.
  괄호로 묶은 만큼 컬럼이 생깁니다.

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `equipment_alarm_log` |
| 출력 | `output` | Table | 파싱된 컬럼이 추가된 로그 |
| 출력 | `output_by_code` | Table | 알람코드별 집계 |

## 스크립트

{{CODE}}

## 핵심 포인트

- **`str.extract(패턴)`**: 괄호 `( )` 로 묶인 캡처 그룹이 각각 하나의 컬럼이 됩니다.
  `(?P<이름>...)` 로 **이름을 붙이면 컬럼명이 자동 지정**되어 훨씬 읽기 좋습니다.
- 자주 쓰는 조각들:

  | 패턴 | 의미 |
  |---|---|
  | `\\d+` | 숫자 1개 이상 |
  | `[\\d.]+` | 숫자와 소수점 |
  | `[A-Z]-\\d+` | `E-1023` 같은 코드 |
  | `\\w+` | 영문/숫자/밑줄 |
  | `.*?` | 최소 매칭 (다음 패턴까지만) |

- **매칭 실패하면 조용히 `NaN`** 이 됩니다. 반드시 `isna().sum()` 으로 파싱 실패 건수를 확인하세요.
  이걸 안 보면 절반이 비어 있는 컬럼으로 분석하게 됩니다.
- 숫자로 뽑은 값은 문자열입니다. **`pd.to_numeric(..., errors="coerce")`** 로 변환하세요.
  `errors="coerce"` 는 변환 실패 시 예외 대신 `NaN` 을 넣습니다. 데이터 함수에서는 이쪽이 안전합니다.
- 정규식은 **AI에게 시키기 가장 좋은 작업**입니다. 사람이 짜면 오래 걸리고 검증도 어렵지만,
  **샘플 문자열 2~3개를 그대로 붙여 주면** 정확한 패턴을 즉시 얻을 수 있습니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. 입력 input, MESSAGE 컬럼을 파싱해줘.
실제 메시지 예시는 아래와 같아 (형식이 조금씩 다를 수 있음):
  [E-1023] Chamber pressure high (LOT=L26043, STEP=ETCH, value=12.34 unit)
  [W-3305] Slurry flow low (LOT=L26101, STEP=CBCMP, value=3.7 unit)
  [I-5000] Recipe changed by operator (LOT=L26008, STEP=PC, value=0.5 unit)

str.extract 를 사용해서 아래 컬럼을 만들어줘. 이름 있는 캡처 그룹 사용.
  ALARM_CODE(E-1023), CODE_TYPE(E/W/I 한 글자), DESCRIPTION(설명 텍스트),
  LOT_ID, STEP, VALUE(숫자형)
- 파싱 실패한 행은 삭제하지 말고 PARSE_OK=False 로 표시
- 파싱 실패 건수를 확인할 수 있게 요약도 만들어줘
- ALARM_CODE 별로 발생 건수/평균 VALUE/영향받은 LOT 수/최초·최종 발생시각 집계
출력: output, output_by_code
```

> 💡 **샘플 문자열을 붙여 주는 것**이 정규식 프롬프트의 핵심입니다.
> 설명만 하면 AI는 추측해서 패턴을 만들고, 그 패턴은 대체로 실제 데이터와 미묘하게 어긋납니다.

## 확인 & 응용

- `PARSE_OK` 가 `False` 인 행을 열어 보세요. 포맷이 다른 예외 케이스가 거기 있습니다.
- **응용**: `str.contains("pressure|flow", case=False)` 로 알람을 대분류해 보세요.
- **응용**: 파싱한 `LOT_ID` 로 `fab_measurement` 와 조인하면
  "알람이 있었던 LOT의 계측값은 달랐는가"를 검증할 수 있습니다.
'''
import numpy as np
import pandas as pd

df = input.copy()

# 이름 있는 캡처 그룹 : 괄호로 묶은 만큼 컬럼이 만들어진다
PATTERN = (
    r"\[(?P<ALARM_CODE>(?P<CODE_TYPE>[A-Z])-\d+)\]\s*"   # [E-1023]
    r"(?P<DESCRIPTION>.*?)\s*"                            # 설명 (최소 매칭)
    r"\(LOT=(?P<LOT_ID>\w+),\s*"                          # LOT=L26043
    r"STEP=(?P<STEP>\w+),\s*"                             # STEP=ETCH
    r"value=(?P<VALUE>[\d.]+)"                            # value=12.34
)

parsed = df["MESSAGE"].str.extract(PATTERN)
df = pd.concat([df, parsed], axis=1)

# 숫자 변환 : errors="coerce" 로 실패 시 예외 대신 NaN
df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")

# 파싱 성공 여부를 반드시 남긴다 (조용한 실패 방지)
df["PARSE_OK"] = df["ALARM_CODE"].notna()

df["ALARM_TIME"] = pd.to_datetime(df["ALARM_TIME"])
df["CODE_TYPE_NAME"] = df["CODE_TYPE"].map({"E": "ERROR", "W": "WARNING", "I": "INFO"}).fillna("UNKNOWN")

# 알람 코드별 집계
ok = df[df["PARSE_OK"]]
by_code = (
    ok.groupby(["ALARM_CODE", "DESCRIPTION"], as_index=False)
    .agg(
        CNT=("ALARM_CODE", "size"),
        EQP_CNT=("EQP_ID", "nunique"),
        LOT_CNT=("LOT_ID", "nunique"),
        VALUE_MEAN=("VALUE", "mean"),
        VALUE_MAX=("VALUE", "max"),
        FIRST_SEEN=("ALARM_TIME", "min"),
        LAST_SEEN=("ALARM_TIME", "max"),
    )
    .sort_values("CNT", ascending=False)
)
by_code["SHARE_PCT"] = (by_code["CNT"] / len(ok) * 100).round(2)
by_code[["VALUE_MEAN", "VALUE_MAX"]] = by_code[["VALUE_MEAN", "VALUE_MAX"]].round(3)
by_code["PARSE_FAIL_TOTAL"] = int((~df["PARSE_OK"]).sum())

output = df
output_by_code = by_code.reset_index(drop=True)

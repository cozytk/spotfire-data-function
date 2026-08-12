---
title: 문법
nav_order: 2
has_children: true
---

# 문법 파트
{: .no_toc }

데이터 함수를 쓰기 위해 알아야 할 것은 생각보다 적습니다.
**Spotfire 쪽 규칙 4가지**와 **pandas 문법 몇 개**가 전부입니다.
{: .fs-5 .fw-300 }

---

## 이 파트에서 다루는 것

| 장 | 내용 | 왜 필요한가 |
|---|---|---|
| [1. 데이터 함수의 구조](./01-structure/) | `input` → 스크립트 → `output` | 이걸 모르면 아무것도 시작 못 함 |
| [2. 입력·출력 파라미터](./02-parameters/) | Value / Column / Table, 마킹·필터링 제한 | **Spotfire만의 고유 기능** |
| [3. 데이터 타입과 결측치](./03-datatypes/) | Spotfire ↔ pandas 타입 매핑 | 타입 오류의 90%가 여기서 발생 |
| [4. 출력 규칙과 자주 나는 오류](./04-output-errors/) | 오류 메시지별 원인과 해결 | 실습 중 막히는 지점 |
| [5. pandas 속성 코스](./05-pandas/) | 실무에서 실제로 쓰는 문법만 | 코드를 **읽고 검증**하기 위해 |
| [6. 등록·디버깅·성능](./06-run-debug/) | 저장, 재계산, print, 속도 | 만든 뒤에 필요한 것들 |
| [7. `spotfire` 모듈](./07-spotfire-module/) | 타입 고정, 메타데이터, 파라미터 조회 | 막판에 막히는 문제들의 해결책 |

{: .팁 }
> **전부 외우려고 하지 마세요.**
> 문법 파트의 목적은 "AI가 준 코드를 읽고 맞는지 판단할 수 있는 수준"입니다.
> 코드를 **처음부터 쓰는 능력**은 이 교육의 목표가 아닙니다.

## 30초 요약

```python
# Spotfire 데이터 함수 = '입력 변수가 이미 만들어진 상태'에서 실행되는 파이썬 스크립트
import pandas as pd          # 1. import 는 스크립트 안에 직접 쓴다

df = input.copy()            # 2. input : Spotfire 가 넣어 준 pandas DataFrame
df = df.drop_duplicates()    # 3. 원하는 처리 (그냥 pandas 코드)

output = df                  # 4. output 에 할당하면 Spotfire 가 가져간다
```

- 입력/출력 **변수 이름은 여러분이 정합니다.** `input`/`output` 은 관례일 뿐입니다.
- 파일을 읽거나 쓰지 않습니다. **변수로 주고받습니다.**
- **시각 컬럼은 `pd.to_datetime()` 으로 변환하고 시작하세요.** `datetime64` 가 아니라 `object` 로 들어옵니다.
  ([타입 매핑](./03-datatypes/))
- `print()` 결과는 **데이터 함수 디버깅을 켜면** 볼 수 있습니다. ([디버깅 방법](./06-run-debug/))
- **인덱스는 Spotfire로 전달되지 않습니다.** `groupby()` 결과는 `reset_index()` 하세요.

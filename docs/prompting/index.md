---
title: AI 활용법
nav_order: 3
has_children: true
---

# 생성형 AI로 데이터 함수 만들기
{: .no_toc }

이 교육의 **핵심 파트**입니다.
pandas를 외우는 대신, **원하는 작업을 정확히 설명해서 코드를 얻어내는 능력**을 기릅니다.
{: .fs-5 .fw-300 }

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## 왜 프롬프트가 중요한가

같은 작업을 요청해도 결과가 이만큼 다릅니다.

<div class="code-example" markdown="1">

**❌ 이렇게 물어보면**

```text
스팟파이어에서 중복 제거하는 파이썬 코드 알려줘
```

돌아오는 답:

```python
import pandas as pd
df = pd.read_csv('data.csv')      # ← 파일을 읽으려 함. 데이터 함수에서는 동작 안 함
df = df.drop_duplicates()
df.to_csv('output.csv')           # ← 파일로 저장. 역시 동작 안 함
print(df.head())                  # ← 보이지 않음
```

**세 줄 모두 데이터 함수에서는 쓸 수 없습니다.**

</div>

<div class="code-example" markdown="1">

**✅ 이렇게 물어보면**

```text
Spotfire Python 데이터 함수를 작성해줘.
입력 변수 input 은 이미 만들어진 pandas DataFrame 이고, 결과는 output 변수에 할당해야 해.
파일 입출력과 print 는 쓸 수 없어.

컬럼: LOT_ID, WAFER_NO, STEP_DESC, MEAS_TIME(문자열 'YYYY-MM-DD HH:MM:SS'), THICKNESS
요구사항:
1. 모든 컬럼이 같은 완전 중복 행 제거
2. LOT_ID+WAFER_NO+STEP_DESC 가 같으면 MEAS_TIME 이 가장 늦은 1건만 남김
3. 제거된 행은 output_removed 로 따로 출력
제약: inplace=True 금지, import 는 스크립트 안에 포함
```

바로 붙여 넣어 동작하는 코드가 나옵니다.

</div>

## 좋은 프롬프트의 5가지 요소

| 요소 | 무엇을 쓰나 | 빠뜨리면 |
|---|---|---|
| **① 환경** | "Spotfire Python 데이터 함수" | 파일 읽기/쓰기 코드가 나옴 |
| **② 입출력 계약** | 변수 이름과 타입 | `output` 할당을 빠뜨림 |
| **③ 데이터 스키마** | 컬럼명, 타입, 예시 값 | 없는 컬럼명을 지어냄 |
| **④ 요구사항** | 번호를 매긴 처리 단계 | 일부만 구현하거나 해석이 달라짐 |
| **⑤ 제약·금지** | "inplace 금지", "apply(axis=1) 금지" | 느리거나 동작 안 하는 코드 |

## 복사해서 쓰는 기본 템플릿

````text
Spotfire Python 데이터 함수를 작성해줘.

[환경]
- 입력 변수는 이미 pandas DataFrame 으로 준비되어 있음 (파일 읽기 불필요)
- 결과는 지정한 출력 변수에 할당 (파일 저장·print 불필요)
- import 는 스크립트 안에 포함
- 사용 가능 패키지: pandas, numpy

[입력]
- input : DataFrame
- (Value 입력이 있다면) threshold : float

[데이터 스키마]
LOT_ID      object   예: 'L26043'
WAFER_NO    int64    1~25
STEP_DESC   object   'PC','RMG','CBCMP','ETCH','PHOTO'
MEAS_TIME   object   '2026-03-02 06:00:00' (문자열)
THICKNESS   float64  결측 있음
PRESSURE    float64  0 은 센서 미취득을 의미

[요구사항]
1. (하고 싶은 일을 번호로)
2.
3.

[제약]
- inplace=True 금지, 재할당 방식 사용
- apply(axis=1) 금지, 벡터 연산(np.select/np.where) 사용
- 0으로 나누기·빈 결과·컬럼 없음 상황을 방어할 것
- 결과가 0행이면 안내용 1행 테이블을 대신 반환할 것

[출력]
- output : 처리 결과 DataFrame
- output_report : 처리 요약 DataFrame

[추가 요청]
- 코드에 한국어 주석을 달아줘
- 이 코드가 무엇을 하는지 3줄로 설명해줘
````

{: .팁 }
> 이 템플릿을 사내 메모장이나 텍스트 확장 도구에 저장해 두고 **매번 붙여 넣어 쓰세요.**
> `[요구사항]` 부분만 바꾸면 됩니다. 프롬프트를 매번 새로 쓰는 사람과 격차가 크게 벌어집니다.

{: .참고 }
> 위 템플릿은 Spotfire 데이터 함수 전용입니다.
> SQL·엑셀·파이썬 스크립트 등 **다른 환경에서도 그대로 쓰는 범용 버전**은
> [범용 프롬프트 템플릿](./04-universal-template/)에 있습니다.
> 환경 블록만 갈아 끼우면 되도록 만들어 두었으니, 데이터 함수 밖의 업무에도 같은 방식으로 쓰세요.

## 스키마를 붙여 넣는 가장 빠른 방법

`[데이터 스키마]` 를 손으로 쓰지 마세요.
Spotfire에서 아래 데이터 함수를 한 번 실행하면 **AI에게 붙여 넣을 스키마 텍스트**가 만들어집니다.

```python
import pandas as pd

df = input
rows = []
for c in df.columns:
    s = df[c]
    sample = s.dropna().head(3).tolist()
    rows.append({
        "COLUMN": c,
        "DTYPE": str(s.dtype),
        "NULL_PCT": round(float(s.isna().mean() * 100), 1),
        "NUNIQUE": int(s.nunique()),
        "SAMPLE": ", ".join(str(v) for v in sample),
    })

output = pd.DataFrame(rows)
```

이 결과 표를 그대로 복사해 프롬프트에 붙이면 **④ 요구사항만 쓰면 되는 상태**가 됩니다.

{: .주의 }
> **실제 데이터 값을 외부 AI 서비스에 붙여 넣기 전에 사내 보안 정책을 반드시 확인하세요.**
> 컬럼명만으로도 충분한 경우가 많고, 값이 필요하다면 형식만 보여 주는
> 가짜 예시 값(`'L26043'`, `520.1`)으로 대체하면 됩니다.
> 이 교안의 예제 데이터가 모두 **가상 데이터**인 것도 같은 이유입니다.

## 작업 흐름

```text
① 무엇을 원하는지 한국어로 정리
        ↓
② 스키마 확보 (위 데이터 함수 실행)
        ↓
③ 템플릿에 채워 넣고 AI에게 요청
        ↓
④ 받은 코드를 '읽는다'  ← 문법 파트가 필요한 이유
        ↓
⑤ Spotfire에 붙여 넣고 실행
        ↓
⑥ 결과 검증 (행 수, 합계, 샘플 확인)
        ↓
   문제가 있으면 → 오류 메시지/증상을 그대로 붙여 재요청 (③ 으로)
```

**④와 ⑥을 건너뛰면 안 됩니다.**
AI가 준 코드는 대체로 잘 동작하지만, **조용히 틀리는 경우**가 가장 위험합니다.
검증 방법은 [결과 검증하기](./03-verify/)에서 다룹니다.

---

## 이 파트의 구성

| 페이지 | 내용 |
|---|---|
| [프롬프트 작성 팁 12가지](./01-tips/) | 결과를 크게 바꾸는 구체적인 요령 |
| [상황별 프롬프트 모음](./02-recipes/) | 복사해서 바로 쓰는 실전 프롬프트 |
| [결과 검증하기](./03-verify/) | 조용히 틀린 코드를 잡아내는 방법 |
| [범용 프롬프트 템플릿](./04-universal-template/) | Spotfire 밖(SQL·엑셀·스크립트)에서도 쓰는 표준 양식 |

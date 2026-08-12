---
title: 6. 등록·디버깅·성능
parent: 문법
nav_order: 6
---

# 6. 등록·디버깅·성능
{: .no_toc }

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## 저장 위치: 분석 파일 vs 라이브러리

| 저장 위치 | 특징 | 언제 |
|---|---|---|
| **분석 파일 안** | 그 `.dxp` 파일에만 존재 | 일회성, 이 분석에서만 쓰는 로직 |
| **라이브러리** | 조직 전체에서 재사용, 버전 관리 | 표준화된 함수 (SPC, 파레토 등) |

{: .팁 }
> 팀에서 자주 쓰는 처리(중복 제거, 결측 대치, 관리도 계산)는 **라이브러리에 저장**해 두고
> 파라미터로 컬럼명을 받도록 만들면([20번 예제](../../examples/20-parameterize/))
> 같은 함수를 여러 분석에서 재사용할 수 있습니다.

## 재계산 동작

데이터 함수 속성에서 설정합니다.

| 설정 | 동작 | 권장 상황 |
|---|---|---|
| 입력 변경 시 자동 재계산 **ON** | 마킹/필터/문서 속성이 바뀌면 즉시 실행 | 마킹 연동, 파라미터 슬라이더 |
| **OFF** | 사용자가 새로 고침할 때만 | 무거운 계산, 대용량 처리 |

{: .주의 }
> 자동 재계산이 켜진 무거운 함수는 **필터를 만질 때마다 화면이 멈춥니다.**
> 실행에 3초 이상 걸린다면 자동 재계산을 끄고, 텍스트 영역에 실행 버튼을 두는 편이 낫습니다.

## 디버깅 방법

### 방법 1. `print()` — 켜 두면 보입니다

데이터 함수의 **표준 출력은 Spotfire가 항상 캡처합니다.** 다만 그것을 화면에 띄울지는 설정에 달려 있습니다.

| 보고 싶은 곳 | 필요한 설정 |
|---|---|
| **데이터 함수 실행 결과** | **`도구 > 옵션 > 데이터 함수`** 에서 **데이터 함수 디버깅을 켠다** |
| 스크립트 편집기에서 바로 실행할 때 | 별도 설정 없이 **출력(Output) 창**에 표시 |
| 오류가 났을 때 | 별도 설정 없이 오류 메시지와 **함께** 표시 |

{: .주의 }
> **디버깅 옵션을 켜지 않으면 성공한 실행의 `print()` 는 보이지 않습니다.**
> "print를 넣었는데 아무것도 안 나온다"의 원인은 대부분 이것입니다.
> 실습을 시작하기 전에 `도구 > 옵션 > 데이터 함수` 에서 디버깅을 먼저 켜 두세요.

설정을 켜고 나면 이렇게 쓸 수 있습니다.

```python
import pandas as pd

df = input.copy()
print("입력:", df.shape)
print(df.dtypes.to_string())

df = df.dropna(subset=["THICKNESS"])
print("결측 제거 후:", df.shape)

output = df
```

표시되는 형태는 이렇습니다. `print()` 로 찍은 내용이 `Standard output:` 아래에 모여 나옵니다.

```text
Standard output:
입력: (11091, 15)
LOT_ID        object
WAFER_NO       Int64
MEAS_TIME     object
THICKNESS    float64
결측 제거 후: (10284, 15)
```

{: .팁 }
> **오류를 만났을 때 가장 먼저 넣어야 할 두 줄**입니다.
> 타입 오류의 원인이 대부분 여기서 바로 보입니다.
>
> ```python
> print(input.dtypes.to_string())          # 어떤 dtype 으로 들어왔는가
> print(input.iloc[0].map(type).to_string())  # 셀 값의 실제 파이썬 타입
> ```

{: .주의 }
> **`print()` 로 대용량 DataFrame을 통째로 찍지 마세요.**
> 출력 문자열이 전부 Spotfire로 넘어가기 때문에 느려지고, 창이 잘립니다.
> `df.head()`, `df.shape`, `df.dtypes` 처럼 **요약만** 찍으세요.
>
> 디버깅용 `print()` 는 완성 후 지우는 것이 좋습니다.
> Web Player에서 여러 사용자가 동시에 실행하면 불필요한 부하가 됩니다.

### 방법 2. 결과를 테이블로 내보내기 (남겨 두고 쓰는 방법)

`print()` 는 실행할 때마다 창을 열어 봐야 합니다.
**대시보드에 상시로 띄워 두고 싶은 진단 정보**는 출력 테이블로 만드세요.

```python
debug = pd.DataFrame(
    [
        {"ITEM": "입력 행 수", "VALUE": str(len(input))},
        {"ITEM": "컬럼 목록", "VALUE": ", ".join(input.columns)},
        {"ITEM": "결측 합계", "VALUE": str(int(input.isna().sum().sum()))},
        {"ITEM": "필터 후 행 수", "VALUE": str(len(df))},
    ]
)
output_debug = debug
```

이 방식은 결과가 **테이블로 남기 때문에** 텍스트 영역에 띄워 두거나
다른 시각화와 연동할 수 있습니다. 개발이 끝나면 이 출력만 제거하면 됩니다.

{: .팁 }
> [`__spotfire_inputs__`](../07-spotfire-module/#3-입력출력-파라미터를-스크립트에서-조회하기) 를 쓰면
> **파라미터 연결 상태까지** 자동으로 진단표에 담을 수 있습니다.

### 방법 3. 오류를 의미 있게 만들기

```python
required = ["LOT_ID", "THICKNESS", "MEAS_TIME"]
missing = [c for c in required if c not in input.columns]
if missing:
    raise ValueError(f"필수 컬럼이 없습니다: {missing} / 현재 컬럼: {list(input.columns)}")
```

사용자에게 "무엇을 고쳐야 하는지"가 바로 전달됩니다.

### 방법 4. 외부 IDE에서 먼저 만들기 (권장)

가장 효율적인 개발 방식입니다.

1. Spotfire에서 데이터를 **CSV로 내보내기**
2. VS Code / Jupyter 등에서 `df = pd.read_csv("...")` 로 읽어 로직 완성
3. 완성된 코드에서 **읽기/쓰기 줄만 제거**하고 `input` / `output` 으로 교체

{: .주의 }
> **여기에 함정이 있습니다.** CSV로 읽은 DataFrame과 Spotfire가 넘겨주는 DataFrame은
> **dtype이 다릅니다.** CSV의 시각 컬럼은 문자열이지만, Spotfire의 DateTime 컬럼은
> `object` 에 담긴 `datetime.datetime` 입니다. 정수 컬럼도 `int64` 가 아니라 `Int64` 입니다.
>
> 그래서 "로컬에서는 되는데 Spotfire에서만 터지는" 코드가 나옵니다.
> 로컬 검증에서도 **입력을 Spotfire와 같은 타입으로 맞춰 두고** 개발하세요.

이 저장소는 그것을 자동화해 두었습니다.
[`scripts/spotfire_sim.py`](https://github.com/cozytk/spotfire-data-function/blob/main/scripts/spotfire_sim.py)
가 CSV를 **Spotfire가 실제로 주는 dtype으로 변환**하고,
출력은 **실제 SBDF로 내보내 봐서** Spotfire가 거부할 결과를 미리 잡아냅니다.

```bash
pip install spotfire                    # 공식 패키지 (선택이지만 권장)
python scripts/run_examples.py          # Spotfire 입출력 규약 그대로 검증
python scripts/run_examples.py --raw    # 재현 없이 CSV 원본 dtype 으로
```

직접 만든 코드도 같은 방식으로 검증할 수 있습니다.

```python
import pandas as pd
from spotfire_sim import to_spotfire_input, check_output

input = to_spotfire_input(pd.read_csv("fab_measurement.csv"))   # Spotfire 입력 재현

# ---- 여기에 데이터 함수 스크립트를 그대로 붙여 넣는다 ----
output = input.copy()
# ------------------------------------------------------

errors, warnings = check_output("output", output)   # Spotfire 가 받아 주는가
print(errors or "출력 OK")
```

## 패키지 관리

- Spotfire Analyst에는 **Python 인터프리터가 번들**되어 있습니다 (설치 폴더의 `Modules` 아래).
- `pandas`, `numpy`, 그리고 데이터 함수 실행 주체인 [`spotfire`](../07-spotfire-module/) 패키지가
  기본 포함되어 있어 **이 교안 예제의 대부분은 추가 설치 없이 동작**합니다.
- 추가 패키지는 **`도구 > Python 도구 > 패키지 관리(Package Management)`** 탭에서
  이름으로 검색해 설치합니다. 내부적으로 **pip 로 PyPI에서** 의존성까지 함께 내려받습니다.
- 사내 정책상 외부 인터넷이 막혀 있으면 설치가 실패할 수 있습니다. **IT 담당 부서에 문의**하세요.

{: .주의 }
> ## 내 PC에 설치했다고 끝이 아닙니다
>
> `패키지 관리` 로 설치한 패키지는 **내 Analyst에만** 들어갑니다.
> 그 분석을 **Web Player(Business Author/Consumer)에서 열면** 계산은 서버의
> **Spotfire Service for Python** 이 수행하므로, **서버에도 같은 패키지가 있어야** 합니다.
>
> 조직에 배포하려면 관리자가 패키지를 **`.spk` (Spotfire Package)** 로 묶어
> 라이브러리에 배포해야 합니다. `spotfire` 패키지가 이 `.spk` 를 만드는 도구를 제공합니다.
>
> **결론**: 서버에서도 돌려야 하는 분석이라면 `scipy`/`scikit-learn` 같은 추가 패키지를
> 쓰기 전에 **먼저 관리자와 협의**하세요. 나중에 발견하면 다시 만들어야 합니다.

이 교안에서 추가 패키지가 필요한 예제:

| 예제 | 패키지 |
|---|---|
| [18. ANOVA](../../examples/18-group-test-anova/) | `scipy` |
| [22. 클러스터링](../../examples/22-kmeans-cluster/) | `scikit-learn` |
| [23. 이미지 출력](../../examples/23-matplotlib-image/) | `matplotlib` |

{: .팁 }
> 설치가 어려운 환경이라면 AI에게 **"numpy만으로 구현해줘"** 라고 요청해 보세요.
> KMeans, 선형회귀, 이동통계 정도는 numpy만으로 충분히 구현됩니다.

## 성능

| 문제 | 해결 |
|---|---|
| 행마다 파이썬 함수 호출 (`apply(axis=1)`) | `np.select` / `np.where` / 벡터 연산 |
| 전체 컬럼 전달 | 입력 파라미터에서 **필요한 컬럼만** 선택 |
| 전체 행 전달 | 입력을 **필터링으로 제한** |
| 반복적인 `merge` | 조인 키에 인덱스를 걸거나 한 번에 처리 |
| 큰 DataFrame 반복 복사 | 필요한 곳에서만 `.copy()` |
| 결과 테이블이 너무 큼 | 원본 반환 대신 **집계 결과만** 반환 |

{: .참고 }
> 데이터 함수의 실행 시간에는 **데이터를 Python으로 옮기고 다시 가져오는 시간**이 포함됩니다.
> 수십만 행 × 수십 컬럼을 통째로 주고받으면, 계산이 빨라도 전송에서 시간이 걸립니다.
> **입력은 최소로, 출력도 최소로.**

## Web Player(서버)에서 쓸 때

분석을 서버에 올려 여러 사람이 볼 예정이라면 아래를 확인하세요.

- 서버 쪽 Python 서비스에도 **같은 패키지가 설치**되어 있어야 합니다.
- 로컬 파일 경로, 네트워크 드라이브 접근 코드는 **반드시 제거**하세요.
- 사용자가 동시에 실행하면 서버 부하가 커집니다. 무거운 함수는 자동 재계산을 끄세요.

---

## 정리

- 표준화된 함수는 **라이브러리에 저장**해 재사용
- 무거운 함수는 **자동 재계산 OFF**
- **`print()` 는 데이터 함수 디버깅을 켜야 보인다** (`도구 > 옵션 > 데이터 함수`) — 요약만 찍을 것
- 상시 진단은 **출력 테이블**로, 개발은 **외부 IDE에서 먼저**
- 로컬 검증은 **입력 dtype을 Spotfire와 맞춘 뒤에** 해야 의미가 있다
- 성능의 핵심은 **입력을 줄이는 것**

다음: [`spotfire` 모듈 — 타입 고정과 메타데이터](../07-spotfire-module/)

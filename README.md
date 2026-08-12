# Spotfire Python 데이터 함수 교안

Spotfire의 기본 기능만으로는 **어렵거나 지나치게 번거로운** 작업을
Python 데이터 함수로 해결하는 방법과, 그 코드를 **생성형 AI에게 정확히 얻어내는 방법**을 다루는 교육 자료입니다.

📖 **교안 사이트: <https://cozytk.github.io/spotfire-data-function/>**

---

## 구성

```
.
├── docs/          교안 사이트 (GitHub Pages, Jekyll + just-the-docs)
├── examples/      데이터 함수 예제 26종 — 설명 + 실행 가능한 코드
├── data/          실습용 CSV 11종 (공개 데이터 + 교육용 가상 데이터)
└── scripts/       데이터 생성 / 예제 실행 검증 / 교안 빌드 스크립트
```

## 예제 26종

| Level | 예제 |
|---|---|
| **1. 정제 기초** | 01 중복 제거·최신값 유지 · 02 결측/0값 정리 · 03 값 치환과 조건부 파생 · 04 조인 후 다중 테이블 분리 · 25 **입력 타입 진단기** |
| **2. 재구조화** | 05 Wide→Long(melt) · 06 피벗/크로스탭 · 07 그룹 통계 되붙이기(transform) · 08 결측 스마트 대치 |
| **3. 시계열·공정** | 09 시간 재집계와 빈 구간 · 10 이동평균/EWMA · 11 이상치 4종 비교 · 12 SPC 관리도+Cp/Cpk+WE룰 · 13 드리프트 기울기·규격 도달 예측 · 14 시간 근접 조인(merge_asof) · 15 연속 이벤트 세션화 · 16 정규식 로그 파싱 |
| **4. 통계·자동화** | 17 상관쌍 랭킹 · 18 ANOVA·사후검정 · 19 파레토/ABC · 20 문서 속성 파라미터화 · 21 **마킹 비교** · 22 KMeans 클러스터링 · 23 matplotlib 이미지 출력 · 24 공개 데이터셋 종합 · 26 **출력 안전장치** |

> **25번과 26번은 데이터 함수의 입구와 출구를 지키는 도구**입니다.
> 25번은 "Spotfire가 실제로 넘겨준 타입"을 보여 주고,
> 26번은 "Spotfire가 결과를 거부하지 않게" 정리합니다. 실무에서 가장 자주 쓰게 되는 두 가지입니다.

각 예제는 **시나리오 → 왜 기본 기능으로는 어려운가 → 데이터 함수 설정 → 코드 → 핵심 포인트 → 프롬프트 예시 → 검증/응용** 순으로 구성되어 있습니다.

## 예제 파일 구조

`examples/*.py` 하나가 **교안 설명과 실행 코드의 단일 원본**입니다.

```python
'''---
title: 예제 제목
inputs: {input: {file: fab_measurement.csv}}
outputs: [output]
---
## 시나리오
(마크다운 설명)

{{CODE}}      ← 이 자리에 아래 코드가 삽입되어 교안 페이지가 만들어짐
'''
import pandas as pd

df = input.copy()          # ← 여기서부터가 Spotfire 에 붙여 넣는 실제 스크립트
output = df.drop_duplicates()
```

- 파일 상단 docstring = 메타데이터 + 교안 본문
- 그 아래 = **Spotfire에 그대로 붙여 넣는 코드**

덕분에 설명과 코드가 어긋날 일이 없고, 모든 예제를 실제로 실행해 검증할 수 있습니다.

## 개발자용: 로컬에서 실행하기

```bash
pip install pandas numpy pyyaml             # 기본
pip install scipy scikit-learn matplotlib   # 18/22/23번 예제용
pip install spotfire                        # 공식 패키지 — 검증 정확도가 올라갑니다

python scripts/make_datasets.py         # 실습 데이터 생성 (시드 고정)
python scripts/run_examples.py          # 예제 26종 전체 실행 검증
python scripts/run_examples.py 12       # 12번만 실행
python scripts/run_examples.py --raw    # Spotfire 타입 재현 없이 CSV 원본 dtype 으로
python scripts/build_docs.py            # examples/ → docs/examples/ 페이지 생성
```

### 검증이 Spotfire와 같은 조건에서 돌아갑니다

`pd.read_csv()` 로 읽은 DataFrame과 Spotfire가 데이터 함수에 넘겨주는 DataFrame은 **dtype이 다릅니다.**
그냥 CSV로 검증하면 "로컬에서는 되는데 Spotfire에서만 터지는" 코드를 놓칩니다.

| | 로컬 `read_csv` | Spotfire 데이터 함수 |
|---|---|---|
| DateTime 컬럼 | `object` (문자열) | `object` (**`datetime.datetime` 객체**) → `.dt` 실패 |
| 정수 컬럼 | `int64` | **`Int64`** (nullable) |
| Boolean 컬럼 | `bool` | `object` (`bool` 객체) |

[`scripts/spotfire_sim.py`](scripts/spotfire_sim.py) 가 이 차이를 메웁니다.

- **입력**: CSV를 Spotfire가 실제로 주는 dtype으로 변환한 뒤 예제를 실행합니다.
- **출력**: 공식 `spotfire` 패키지가 설치되어 있으면 **실제 SBDF로 내보내 봅니다.**
  Spotfire가 거부할 결과(전부 결측 컬럼, 셀 안의 list, 혼합 타입, 중복 컬럼명)면
  **여기서 똑같이 실패**하므로, 교안의 모든 코드가 Spotfire에서 동작함을 보장합니다.
  패키지가 없으면 규칙 기반 점검으로 자동 대체됩니다.

### 교안 사이트 로컬 미리보기

```bash
cd docs
bundle install
bundle exec jekyll serve --config _config.yml,_config.local.yml
# http://localhost:4000/spotfire-data-function/
```

로컬에서는 `_config.local.yml` 로 테마를 젬(`just-the-docs`)에서 직접 읽습니다.
GitHub 빌더는 `_config.yml` 의 `remote_theme` 로 테마를 내려받습니다.

## 배포

**Settings → Pages → Source: Deploy from a branch** (기본값) 상태에서
기본 브랜치의 `docs/` 폴더를 지정하면, GitHub 기본 빌더가 자동으로 빌드·배포합니다.
`_config.yml` 이 `remote_theme` 를 쓰기 때문에 별도 설정 없이 동작합니다.

> 기본 빌더는 `github-pages` 젬 세트(Jekyll 3.10)를 사용하며 저장소의 `Gemfile` 을 무시합니다.
> `theme:` 로 지정한 테마는 인식하지 못하므로 **반드시 `remote_theme:` 를 써야 합니다.**

Pages 소스를 **GitHub Actions** 로 바꿔서 쓰고 싶다면
`.github/workflows/pages.yml` 을 Actions 탭에서 수동 실행하세요
(examples → docs 페이지 재생성까지 포함해 빌드합니다).

## 데이터 출처

- `titanic.csv` — [datasciencedojo/datasets](https://github.com/datasciencedojo/datasets)
- `iris.csv` — [seaborn-data](https://github.com/mwaskom/seaborn-data)
- `diabetes_train.csv` / `diabetes_test.csv` — Pima Indians Diabetes ([jbrownlee/Datasets](https://github.com/jbrownlee/Datasets))
- 그 외 CSV — `scripts/make_datasets.py` 로 생성한 **교육용 가상 데이터** (사내 실제 데이터 아님)

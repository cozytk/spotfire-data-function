---
title: "22. LOT 프로파일 클러스터링 (KMeans)"
parent: 예제 모음
nav_order: 22
---

# 22. LOT 프로파일 클러스터링 (KMeans)
{: .no_toc }

**난이도** ★★★ · **Level 4 · 통계·자동화·Spotfire 고유 기능**

여러 공정의 계측값을 하나의 프로파일로 묶어 비슷한 LOT끼리 자동 분류하고, 각 군집의 특징을 해석 가능한 표로 만듭니다.

> **추가 패키지 필요**: `scikit-learn` — `도구 > Python 도구 > 패키지 관리` 에서 설치

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/22_kmeans_cluster.py)

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
| 입력 | `n_clusters` | Value | 문서 속성 (예: `4`) |
| 출력 | `output` | Table | 새 데이터 테이블 |
| 출력 | `output_center` | Table | 새 데이터 테이블 |

---

## 시나리오

LOT 하나에는 5개 공정의 계측값이 있습니다. 이 5개 값을 **하나의 지문(프로파일)** 으로 보고
"비슷한 LOT끼리" 묶으면, 눈으로는 안 보이던 패턴이 드러납니다.

- 특정 군집에 저수율 LOT이 몰려 있는가?
- 그 군집은 어떤 공정 값이 특이한가?

## 왜 Spotfire 기본 기능으로는 어려운가

- Spotfire에도 클러스터링 기능이 있지만 (계층적 군집화),
  **전처리(피벗 → 표준화 → 결측 처리)** 를 데이터 함수 없이 준비하는 것이 이미 큰 일입니다.
- **표준화(StandardScaler)** 를 빠뜨리면 스케일이 큰 컬럼(CBCMP 980)이 작은 컬럼(PHOTO 88)을 압도해
  군집이 사실상 한 컬럼으로 결정됩니다. 이 함정을 기본 기능만으로 피하기 어렵습니다.
- 군집 결과를 **원본 테이블에 라벨로 되돌려 주는 것**, **군집 중심을 해석 가능한 표로 만드는 것**은
  데이터 함수의 몫입니다.

## ⚠️ 패키지 안내

**`scikit-learn`** 이 필요합니다. `도구 > Python 도구 > 패키지 관리` 에서 설치하세요.
설치가 불가능한 환경이라면 **numpy만으로 KMeans를 20줄 정도로 직접 구현**할 수도 있습니다
(AI에게 "sklearn 없이 numpy만으로 KMeans 구현해줘"라고 요청하면 됩니다).

## 데이터 함수 설정

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 입력 | `n_clusters` | Value (Integer) | 문서 속성 `NClusters` (슬라이더 2~8) |
| 출력 | `output` | Table | LOT별 프로파일 + 군집 라벨 |
| 출력 | `output_center` | Table | 군집 중심 프로파일 (해석용) |

## 스크립트

```python
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

df = input.copy()

# 1) 특징 행렬 : LOT 하나 = 한 행, 공정 = 컬럼
feat = df.pivot_table(index="LOT_ID", columns="STEP_DESC", values="THICKNESS", aggfunc="mean")
feat.columns = [str(c) for c in feat.columns]

# 2) 결측 처리 : 전부 결측인 LOT 제외 후 컬럼 중앙값 대치
feat = feat.dropna(how="all")
feat = feat.fillna(feat.median())

k = max(2, min(int(n_clusters), len(feat) - 1))

# 3) 표준화 : 스케일이 큰 공정(CBCMP ~980)이 작은 공정(PHOTO ~88)을 압도하는 것을 막는다.
#    이 단계를 빼면 군집이 사실상 한 컬럼으로만 결정된다.
scaler = StandardScaler()
X = scaler.fit_transform(feat.to_numpy())

# 4) KMeans : random_state 고정 -> 실행할 때마다 군집 번호가 바뀌지 않는다
km = KMeans(n_clusters=k, random_state=42, n_init=10)
labels = km.fit_predict(X)
sil = silhouette_score(X, labels) if len(set(labels)) > 1 else np.nan

res = feat.reset_index()
res["CLUSTER"] = ["C" + str(v) for v in labels]
res["SILHOUETTE_SCORE"] = round(float(sil), 4)
res["N_CLUSTERS"] = k

# 5) 군집 중심을 원래 스케일로 되돌려 해석 가능한 표로
centers = pd.DataFrame(scaler.inverse_transform(km.cluster_centers_), columns=feat.columns)
centers.insert(0, "CLUSTER", ["C" + str(i) for i in range(k)])
centers["N_LOTS"] = [int((labels == i).sum()) for i in range(k)]

overall = feat.mean()
overall_std = feat.std().replace(0, np.nan)

# 각 공정이 전체 평균 대비 얼마나 높/낮은지(표준화 편차)로 해석 문장을 만든다
feature_cols = list(feat.columns)
notes = []
for _, row in centers.iterrows():
    z = {c: (row[c] - overall[c]) / overall_std[c] for c in feature_cols}
    high = [c for c, v in z.items() if v >= 0.5]
    low = [c for c, v in z.items() if v <= -0.5]
    parts = [f"{c} 높음" for c in high] + [f"{c} 낮음" for c in low]
    notes.append(", ".join(parts) if parts else "전 공정 평균 수준")
centers["PROFILE"] = notes
centers[feature_cols] = centers[feature_cols].round(3)

output = res
output_center = centers
```

## 핵심 포인트

- **순서가 전부입니다: 피벗 → 결측 처리 → 표준화 → 클러스터링.**
  표준화를 건너뛰면 결과가 의미 없어집니다. 이건 선택이 아니라 필수입니다.
- `pivot_table` 로 "LOT 하나 = 한 행, 공정 = 컬럼" 형태(**특징 행렬**)를 만드는 것이 첫 단계입니다.
  머신러닝에 데이터를 넣기 전에는 항상 이 모양을 만들어야 합니다.
- `random_state` 를 **반드시 고정**하세요. 고정하지 않으면 **실행할 때마다 군집 번호가 바뀝니다.**
  사용자가 새로고침할 때마다 색이 바뀌는 대시보드가 됩니다.
- 군집 번호(0,1,2)는 **아무 의미가 없습니다.** 그래서 `output_center` 로 각 군집의 특징을
  **"어느 공정이 평균보다 높은/낮은가"** 문장으로 만들어 주는 것이 실무에서 결정적입니다.
- 클러스터 개수는 정답이 없습니다. `n_clusters` 를 슬라이더로 빼서 **사용자가 탐색**하게 하세요.
  실루엣 점수를 함께 출력하면 판단에 도움이 됩니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. scikit-learn 사용.
입력: input(계측 데이터), n_clusters(int)
컬럼: LOT_ID, STEP_DESC, THICKNESS

1. LOT_ID 를 행, STEP_DESC 를 열, THICKNESS 평균을 값으로 하는 특징 행렬 생성
2. 결측은 각 컬럼 중앙값으로 대치. 모든 값이 결측인 LOT 은 제외
3. StandardScaler 로 표준화한 뒤 KMeans(n_clusters, random_state=42, n_init=10) 수행
4. 실루엣 점수를 계산해서 컬럼으로 포함
5. 각 LOT 에 CLUSTER 라벨(문자열 'C0','C1'...)을 붙여 output 으로
6. 군집 중심을 원래 스케일로 되돌린 표를 output_center 로.
   각 공정별로 전체 평균 대비 높음/낮음/보통을 판정한 해석 컬럼과,
   군집별 LOT 수, 대표 특징 문장(예: 'CBCMP 높음, ETCH 낮음')도 포함
random_state 를 고정해서 실행할 때마다 결과가 바뀌지 않게 해줘.
표준화를 반드시 적용하고, 왜 필요한지 주석으로 설명해줘.
```

## 확인 & 응용

- `output` 의 `CLUSTER` 를 `wafer_yield.csv` 와 조인해 **군집별 평균 수율**을 비교해 보세요.
  특정 군집의 수율이 낮다면 그 군집의 프로파일이 곧 원인 가설입니다.
- **응용**: `iris.csv` 로 같은 코드를 돌려 실제 품종과 비교하면 클러스터링의 동작을 직관적으로 이해할 수 있습니다.
- **응용**: `n_clusters` 를 2~8로 바꿔 가며 실루엣 점수가 최대가 되는 값을 찾아보세요.

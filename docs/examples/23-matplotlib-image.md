---
title: 23. 차트 이미지를 데이터 함수로 만들어 대시보드에 띄우기
parent: 예제 모음
nav_order: 23
---

# 23. 차트 이미지를 데이터 함수로 만들어 대시보드에 띄우기
{: .no_toc }

**난이도** ★★★ · **Level 4 · 통계·자동화·Spotfire 고유 기능**

Spotfire 시각화로는 그릴 수 없는 그림(설비별 분포 비교, 관리도 격자)을 matplotlib으로 그려 문서 속성 이미지로 내보냅니다.

> **추가 패키지 필요**: `matplotlib` — `도구 > Python 도구 > 패키지 관리` 에서 설치

사용 데이터: [`fab_measurement.csv`](https://github.com/cozytk/spotfire-data-function/blob/main/data/fab_measurement.csv) · [스크립트 원본](https://github.com/cozytk/spotfire-data-function/blob/main/examples/23_matplotlib_image.py)

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
| 출력 | `output_image` | Table | 새 데이터 테이블 |
| 출력 | `output_stats` | Table | 새 데이터 테이블 |

---

## 시나리오

Spotfire 시각화는 강력하지만 못 그리는 그림이 있습니다.

- 설비별 **바이올린 플롯 / 밀도 곡선**
- 규격선·관리한계선이 함께 들어간 **격자형 관리도(small multiples)**
- 통계 패키지 특유의 진단 플롯 (Q-Q plot, 잔차도 등)

이런 그림은 matplotlib으로 그려서 **이미지로 대시보드에 얹는 것**이 가장 빠릅니다.

## 어떻게 동작하나

데이터 함수의 출력을 **`Value` 타입 / Spotfire 데이터 타입 `Binary`** 로 선언하고
**문서 속성**에 연결하면, Spotfire가 그림 객체를 이미지 바이너리로 변환해 저장합니다.
그 뒤 **텍스트 영역 → 이미지 삽입 → "문서 속성의 이미지"** 로 화면에 표시합니다.

| 구분 | 파라미터명 | 타입 | 연결 대상 |
|---|---|---|---|
| 입력 | `input` | Table | `fab_measurement` |
| 출력 | `output_image` | Value (**Binary**) | 문서 속성 `ChartImage` |
| 출력 | `output_stats` | Table | 그림에 쓰인 통계 값 |

> 버전에 따라 지원되는 그림 객체 형식이 다를 수 있습니다. 잘 표시되지 않으면
> `matplotlib` **Figure 객체를 그대로 반환**하는 방식과, **PNG 바이트로 직접 변환**해서 반환하는 방식을
> 둘 다 시도해 보세요. 아래 코드는 두 방법을 모두 담고 있습니다.

## 스크립트

```python
import io

import matplotlib

matplotlib.use("Agg")  # 화면 없는 환경 필수 설정 — 맨 위에서 먼저 지정한다

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 한글 깨짐 방지 (환경에 설치된 폰트에 맞춰 조정)
for font in ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]:
    if font in {f.name for f in matplotlib.font_manager.fontManager.ttflist}:
        plt.rcParams["font.family"] = font
        break
plt.rcParams["axes.unicode_minus"] = False

df = input.copy().dropna(subset=["THICKNESS"])
SPEC = {"PC": 520.0, "RMG": 310.0, "CBCMP": 980.0, "ETCH": 145.0, "PHOTO": 88.0}

steps = [s for s in SPEC if s in set(df["STEP_DESC"])]
n = max(1, len(steps))
ncols = 3
nrows = int(np.ceil(n / ncols))

fig, axes = plt.subplots(nrows, ncols, figsize=(15, 4 * nrows))
axes = np.atleast_1d(axes).ravel()

stats_rows = []
for ax, step in zip(axes, steps):
    block = df[df["STEP_DESC"] == step]
    center = SPEC[step]
    mu, sd = block["THICKNESS"].mean(), block["THICKNESS"].std()

    for eqp, sub in block.groupby("EQP_ID"):
        ax.hist(sub["THICKNESS"], bins=40, alpha=0.55, label=f"{eqp} (n={len(sub)})")

    ax.axvline(center, color="black", linestyle="--", linewidth=1.2, label="규격 중심")
    ax.axvline(mu + 3 * sd, color="red", linestyle=":", linewidth=1.0)
    ax.axvline(mu - 3 * sd, color="red", linestyle=":", linewidth=1.0, label="±3σ")
    ax.set_title(f"{step}  (n={len(block):,}, μ={mu:.2f}, σ={sd:.2f})")
    ax.set_xlabel("THICKNESS")
    ax.set_ylabel("빈도")
    ax.legend(fontsize=8)

    stats_rows.append({"STEP_DESC": step, "N": len(block), "MEAN": round(float(mu), 3),
                       "STD": round(float(sd), 3), "SPEC_CENTER": center,
                       "UCL_3S": round(float(mu + 3 * sd), 3), "LCL_3S": round(float(mu - 3 * sd), 3)})

for ax in axes[len(steps):]:      # 남는 칸 숨기기
    ax.set_visible(False)

fig.suptitle("공정별 두께 분포 (설비 중첩 비교)", fontsize=14)
fig.tight_layout()

# 방법 A : Figure 객체를 그대로 반환 (Spotfire 가 이미지로 변환)
output_image = fig

# 방법 B : PNG 바이트로 직접 변환해 반환 (A 가 동작하지 않을 때)
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
image_bytes = buf.getvalue()
# output_image = image_bytes      # ← 방법 A 가 안 되면 이 줄의 주석을 해제

plt.close(fig)  # 메모리 누수 방지 : 반드시 닫는다

output_stats = pd.DataFrame(stats_rows) if stats_rows else pd.DataFrame(
    [{"STEP_DESC": "NO_DATA", "N": 0, "MEAN": 0.0, "STD": 0.0,
      "SPEC_CENTER": 0.0, "UCL_3S": 0.0, "LCL_3S": 0.0}]
)
```

## 핵심 포인트

- **`matplotlib.use("Agg")` 를 반드시 맨 위에.** 화면 없는 환경에서 GUI 백엔드를 잡으려다
  데이터 함수가 멈추거나 죽는 것을 막아 줍니다. 이건 관례가 아니라 필수입니다.
- **한글 폰트**: 기본 폰트에는 한글이 없어 네모(□)로 깨집니다.
  `plt.rcParams["font.family"] = "Malgun Gothic"` (Windows 기준)을 설정하고,
  `axes.unicode_minus = False` 로 음수 기호 깨짐도 함께 잡으세요.
- `plt.close(fig)` 로 **반드시 닫으세요.** 데이터 함수가 반복 실행되면 그림 객체가 쌓여 메모리를 먹습니다.
- 이미지는 **데이터가 아닙니다.** 필터·마킹과 연동되지 않고, 확대하면 깨집니다.
  → Spotfire 기본 시각화로 그릴 수 있는 것은 **그냥 Spotfire로 그리세요.**
  이 방법은 "Spotfire로는 못 그리는 그림"에만 쓰는 것이 원칙입니다.
- 그림에 사용된 **수치를 테이블로 함께 출력**하면 "이 선은 무슨 값이냐"는 질문에 바로 답할 수 있습니다.

## 이렇게 물어보세요 (프롬프트)

```text
Spotfire Python 데이터 함수. matplotlib 으로 그림을 그려 문서 속성(Binary)으로 내보낼 거야.
입력 input, 컬럼: EQP_ID, STEP_DESC, THICKNESS, MEAS_TIME

1. matplotlib 은 Agg 백엔드로 설정하고 한글 폰트/음수기호 설정을 넣어줘
2. STEP_DESC 별로 subplot 격자를 만들어, 각 칸에 설비별 THICKNESS 분포를 겹친 히스토그램으로 그려줘
   - 각 칸에 규격 중심선(점선)과 ±3sigma 선을 표시
   - 제목에 공정명과 표본 수 표시
3. 그림 객체를 output_image 변수에 할당 (Binary 출력용)
4. 그림에 사용된 통계값(공정별 평균/표준편차/표본수)을 output_stats 테이블로도 내보내줘
5. 다 그린 후 plt.close 로 정리하고, 데이터가 없을 때도 죽지 않게 방어해줘
```

## 확인 & 응용

- 텍스트 영역에 이미지를 넣고, 데이터 함수를 **"자동 다시 계산"** 으로 두면 필터 변경 시 그림이 갱신됩니다.
- **응용**: `seaborn` 을 설치하면 `violinplot`, `pairplot` 을 몇 줄로 그릴 수 있습니다.
- **응용**: [12번 예제](../12-spc-control-chart/)의 관리도를 설비별 격자로 그려 한 장으로 만들어 보세요.

---
title: 상황별 프롬프트 모음
parent: AI 활용법
nav_order: 2
---

# 상황별 프롬프트 모음
{: .no_toc }

복사해서 `[...]` 부분만 바꿔 쓰는 실전 프롬프트입니다.
{: .fs-5 .fw-300 }

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## A. 데이터 정제

### A-1. 중복 제거

```text
Spotfire Python 데이터 함수. 입력 input(DataFrame), 출력 output.
1. 모든 컬럼이 동일한 완전 중복 행 제거
2. [LOT_ID, WAFER_NO, STEP_DESC] 가 같으면 중복으로 보고,
   [MEAS_TIME] 이 가장 늦은 1건만 남김 (정렬 후 처리할 것)
3. 제거된 행은 output_removed 로 별도 출력
inplace 금지. reset_index(drop=True) 로 마무리.
```

### A-2. 결측치 처리

```text
Spotfire Python 데이터 함수. 입력 input.
컬럼별로 결측 처리를 다르게 적용해줘.
- [THICKNESS, CD] : [EQP_ID, STEP_DESC] 그룹 중앙값으로 대치, 그룹 전체 결측이면 전체 중앙값
- [TEMP] : [EQP_ID] 별 시간 선형 보간, 연속 결측 3칸 초과는 채우지 말 것
- [CHAMBER] : 직전 값 → 이후 값 → 'UNKNOWN'
각 컬럼에 <컬럼명>_IMPUTED 플래그를 만들고, 컬럼별 대치 건수 리포트도 출력.
```

### A-3. 이상값 행 제거 (0 포함)

```text
Spotfire Python 데이터 함수. 입력 input.
1. [THICKNESS, CD] 가 결측인 행 제거
2. [PRESSURE, TEMP] 가 0 인 행 제거 — 이 컬럼들에서 0은 센서 미취득을 의미함
   단 [PARTICLE_CNT, WAFER_NO] 의 0은 정상값이므로 절대 건드리지 말 것
3. 문자열 컬럼의 빈 문자열/공백은 결측으로 간주해 통일
전체 컬럼을 일괄 검사하는 방식은 쓰지 마.
단계별 제거 건수 리포트를 output_report 로 출력.
```

### A-4. 코드값 정리와 표준화

```text
Spotfire Python 데이터 함수. 입력 input.
1. [IS_DEFECT] 의 'REAL','R','Y' 를 'TRUE' 로 통일, 나머지는 'FALSE'
2. [EQP_ID] 앞뒤 공백 제거 후 대문자 통일
3. [MEAS_TIME] 을 datetime 으로 변환 (변환 실패는 NaT)
4. 정리 전후 고유값 목록을 비교할 수 있는 요약 테이블도 출력
```

---

## B. 구조 변환

### B-1. Wide → Long

```text
Spotfire Python 데이터 함수. 입력 input 은 wide 포맷.
키 컬럼은 [TIMESTAMP, EQP_ID] 이고 나머지는 전부 값 컬럼이야. 값 컬럼 수는 그때그때 달라져.
1. 키를 제외한 나머지를 자동으로 찾아 long 포맷(키 + NAME + VALUE)으로 변환
2. VALUE 가 결측인 행 제외
3. NAME 에서 숫자만 추출해 NO 컬럼(정수) 추가
컬럼명을 하드코딩하지 말 것.
```

### B-2. 크로스탭 / 피벗

```text
Spotfire Python 데이터 함수. 입력 input.
행=[EQP_ID], 열=[CHAMBER], 값=[불량률(%)] 인 피벗 테이블을 만들어줘.
- 불량률 = IS_DEFECT 가 'TRUE' 인 비율 × 100, 소수 둘째 자리
- 합계행/합계열 포함
- MultiIndex 를 평탄화하고 모든 컬럼명을 문자열로 만들어 Spotfire 로 내보낼 수 있게 할 것
- 같은 내용의 long 포맷도 히트맵용으로 함께 출력
```

### B-3. 여러 테이블로 분리

```text
Spotfire Python 데이터 함수. 입력 input.
[STEP_DESC] 값에 따라 테이블을 나눠줘.
- 'PC' → output1
- 'RMG' → output2
- 그 외 전부 → output3
어떤 행도 누락되지 않게 마지막은 '그 외 전부'로 받을 것.
각 출력이 0행이면 컬럼 dtype 에 맞는 기본값이 든 1행을 대신 넣어줘 (빈 테이블 출력 방지).
```

### B-4. 조인

```text
Spotfire Python 데이터 함수. 입력 input1, input2. 조인 키는 [JOIN_ID].
1. 양쪽 키의 공백/대소문자를 정규화한 뒤 left join
2. 조인 전에 오른쪽 테이블 키 중복을 검사하고, 중복이면 첫 행만 사용
3. indicator 로 매칭 여부를 확인하고, 매칭 실패 행은 output_unmatched 로 분리
4. 매칭률(%)을 요약 테이블로 출력
```

---

## C. 집계와 통계

### C-1. 그룹 통계를 원본에 되붙이기

```text
Spotfire Python 데이터 함수. 입력 input.
그룹 키 [EQP_ID, STEP_DESC], 대상 값 [THICKNESS].
원본 행 수를 유지한 채(groupby().transform() 사용) 아래 컬럼 추가:
GRP_N, GRP_MEAN, GRP_STD, GRP_MEDIAN, Z_SCORE, ROBUST_Z(MAD 기반), PCTL(그룹 내 백분위)
표준편차나 MAD 가 0인 경우 0으로 나누지 않도록 방어할 것.
```

### C-2. 이상치 탐지

```text
Spotfire Python 데이터 함수. 입력 input, 그룹 [EQP_ID], 값 [THICKNESS].
아래 4가지 기준으로 각각 이상치 플래그를 만들어줘 (행은 삭제하지 말고 플래그만):
1. IQR : Q1-1.5*IQR ~ Q3+1.5*IQR 밖
2. Z-score : |z| > 3
3. MAD : 0.6745*(x-median)/MAD 의 절대값 > 3.5
4. Hampel : 창 11 이동중앙값 기준 |x-중앙값| > 3*1.4826*이동MAD
그리고 몇 개 기준에서 걸렸는지 VOTES 컬럼과 등급(확실/의심/경미/정상) 추가.
방법별 검출 건수 비교표도 출력.
```

### C-3. SPC 관리도

```text
Spotfire Python 데이터 함수. SPC 개별값 관리도(I chart)를 만들어줘.
입력 input, 그룹 [EQP_ID, STEP_DESC], 값 [THICKNESS], 시간 [MEAS_TIME].
1. CL = 그룹 평균, sigma_hat = 이동범위 평균/1.128, UCL/LCL = CL ± 3*sigma_hat
2. Western Electric 룰 구현 (각각 별도 컬럼):
   Rule1: 1점이 3시그마 밖
   Rule2: 연속 9점이 중심선 같은 쪽
   Rule3: 연속 6점 연속 상승 또는 하강
   Rule5: 연속 3점 중 2점이 같은 쪽 2시그마 밖
3. 규격이 [PC 520±3%, CBCMP 980±2%] 일 때 그룹별 Cp/Cpk/Pp/Ppk 계산
   표본 30개 미만 그룹은 '표본부족' 으로 표시하고 계산하지 말 것
4. 룰 위반 지점만 모은 테이블 별도 출력
groupby+transform+rolling 으로 벡터화, apply(axis=1) 금지.
```

### C-4. 통계 검정

```text
Spotfire Python 데이터 함수. scipy.stats 사용.
입력 input, alpha=0.05.
[STEP_DESC] 별로 [EQP_ID] 를 그룹으로 하는 일원분산분석(ANOVA)을 수행하고,
유의한 경우 설비 쌍별 Welch t-test 사후검정(Bonferroni 보정)을 해줘.
Cohen's d 효과크기와 해석(미미/작음/중간/큼)도 포함.
표본 30개 미만 그룹은 제외. 비모수 Kruskal-Wallis 결과도 함께.
결과: output_anova, output_posthoc
```

### C-5. 파레토 / ABC

```text
Spotfire Python 데이터 함수. 입력 input.
[CUSTOMER] 별 [AMOUNT_USD] 합계를 기준으로 파레토 분석을 해줘.
1. [STATUS] 가 'CANCELLED' 인 행 제외
2. 금액 내림차순 정렬 후 누적금액, 누적비율(%), 전체 대비 비중, 순위
3. ABC 등급: 누적비율 80%까지 A, 95%까지 B, 나머지 C
   단 경계를 처음 넘는 항목은 상위 등급에 포함시킬 것(직전 누적비율로 판정)
4. 등급별 요약(항목 수, 금액 합, 비중)도 출력
```

---

## D. 시계열

### D-1. 시간 단위 재집계 + 빈 구간

```text
Spotfire Python 데이터 함수. 입력 input, freq='1h'.
[EQP_ID] 별로 [MEAS_TIME] 을 freq 단위로 재집계해줘.
1. 집계: 건수, [THICKNESS] 평균/표준편차
2. 모든 설비가 전체 데이터의 최소~최대 시각 범위를 공통으로 갖도록 빈 구간도 행으로 만들 것
3. 데이터가 없는 구간은 건수=0, 측정값은 NaN 으로 (0으로 채우지 말 것)
4. 연속으로 비어 있는 구간을 묶어 (설비, 시작, 종료, 시간) 형태로 별도 출력
```

### D-2. 이동 통계

```text
Spotfire Python 데이터 함수. 입력 input, window=25.
[EQP_ID, STEP_DESC] 그룹 안에서 [MEAS_TIME] 순으로 정렬한 뒤
[THICKNESS] 의 이동평균(window), 장기이동평균(window*4), 이동표준편차, EWMA(span=window) 추가.
min_periods 는 window 의 절반으로. groupby().transform() 사용.
단기평균이 장기평균을 상향/하향 돌파하는 지점에 CROSS 표시하고 그 지점만 별도 출력.
```

### D-3. 연속 구간(세션) 묶기

```text
Spotfire Python 데이터 함수. 입력 input, gap_minutes=30.
[EQP_ID] 안에서 직전 행과의 [ALARM_TIME] 간격이 gap_minutes 를 넘으면 새 세션으로 봐줘.
shift/diff/cumsum 으로 SESSION_ID 를 만들고,
세션별 시작/종료/지속시간(분)/건수/최고심각도/대표메시지를 요약해줘. for 루프 금지.
```

### D-4. 시간 근접 조인

```text
Spotfire Python 데이터 함수. pandas.merge_asof 사용.
input1(계측, MEAS_TIME), input2(센서, TIMESTAMP), tolerance_min=60.
각 계측 행에 같은 [EQP_ID] 의 센서 데이터 중 MEAS_TIME '이전'의 가장 가까운 값을 붙여줘.
- 시간차가 tolerance_min 을 넘으면 매칭하지 말 것
- 실제 매칭된 시각과 시간차(분)를 컬럼으로 남길 것
- merge_asof 의 전제조건(양쪽 시간 정렬, by 지정, dtype 일치)을 코드에 반영하고 주석으로 설명
- 설비별 매칭 성공률 요약도 출력
```

### D-5. 회귀 기울기 / 추세

```text
Spotfire Python 데이터 함수. numpy 만 사용(sklearn 금지).
[EQP_ID, STEP_DESC] 그룹별로 [THICKNESS] 를 '경과 일수'에 대해 1차 회귀해서
SLOPE_PER_DAY, INTERCEPT, R2, N, 기간을 계산해줘.
- X축은 그룹 내 최초 시각 기준 경과 일수(float)
- 표본 30개 미만, 기간 1일 미만 그룹 제외
- |기울기| 내림차순 랭킹
- 현재 추세가 유지될 때 규격([PC 520±3%]) 도달까지 남은 일수와 예상 날짜도 계산
  R2 < 0.3 이면 '추세없음'으로 표기하고 예측하지 말 것
```

---

## E. 텍스트 처리

### E-1. 정규식 파싱

````text
Spotfire Python 데이터 함수. [MESSAGE] 컬럼을 파싱해줘.
실제 값 예시:
  [E-1023] Chamber pressure high (LOT=L26043, STEP=ETCH, value=12.34 unit)
  [W-3305] Slurry flow low (LOT=L26101, STEP=CBCMP, value=3.7 unit)

str.extract 와 이름 있는 캡처 그룹으로 아래 컬럼을 만들어줘:
ALARM_CODE, CODE_TYPE(첫 글자), DESCRIPTION, LOT_ID, STEP, VALUE(숫자형)
- 파싱 실패 행은 삭제하지 말고 PARSE_OK=False 로 표시
- 파싱 실패 건수를 확인할 수 있게 할 것
````

### E-2. 분류·키워드 태깅

```text
Spotfire Python 데이터 함수. [MESSAGE] 를 키워드로 분류해줘.
- 'pressure|vacuum' 포함 → '압력계'
- 'flow|slurry' 포함 → '유량계'
- 'temp|thermal' 포함 → '온도계'
- 그 외 → '기타'
대소문자 무시, 결측 안전 처리(na=False). np.select 사용.
분류별 건수 요약도 함께.
```

---

## F. 파라미터화·Spotfire 고유 기능

### F-1. 문서 속성으로 파라미터화

```text
Spotfire Python 데이터 함수. 재사용 가능한 범용 집계 함수를 만들어줘.
입력:
- input : DataFrame
- group_cols : 문자열, 세미콜론 구분 그룹 컬럼 목록 (Spotfire Value 입력은 리스트를 못 넘기므로)
- value_col : 문자열, 집계 대상 컬럼
- agg_list : 문자열, 세미콜론 구분 집계 함수 (mean;std;median;count)
- threshold : float
요구:
1. 입력값 검증 — 없는 컬럼/함수는 무시하고, 전부 무효면 기본값 사용
2. 집계 결과 컬럼명은 "<value_col>_<함수명>"
3. 표준편차 > threshold 면 ALERT 표시
4. 실행 조건(그룹/기간/행수)을 output_meta 로 함께 출력
예외가 나도 함수가 죽지 않게 방어적으로 작성.
```

### F-2. 마킹 비교

```text
Spotfire Python 데이터 함수. 마킹 비교 분석이야.
입력: input_marked(마킹된 행, 0행일 수 있음), input_all(전체 행)
1. input_marked 가 비어 있으면 오류 대신 '차트에서 데이터를 선택하세요' 안내 1행 반환
2. 전체에서 마킹된 행을 제외한 '나머지'와 비교할 것 (전체와 비교하면 차이가 희석됨)
3. 숫자 컬럼별 마킹평균/나머지평균/차이/표준화차이, 차이 큰 순 정렬
4. 범주형 컬럼별 분포 비교와 LIFT(마킹비율/나머지비율), LIFT 2 이상은 '쏠림' 표시
```

### F-3. 차트 이미지 출력

```text
Spotfire Python 데이터 함수. matplotlib 으로 그림을 그려 문서 속성(Binary)으로 내보낼 거야.
1. matplotlib.use("Agg") 를 맨 위에 설정하고 한글 폰트/음수기호 설정 포함
2. [STEP_DESC] 별 subplot 격자에 설비별 [THICKNESS] 히스토그램을 겹쳐 그리고
   규격 중심선과 ±3시그마 선 표시
3. Figure 객체를 output_image 에 할당
4. 그림에 쓰인 통계값도 테이블로 출력
5. plt.close 로 정리하고 데이터가 없을 때도 죽지 않게 방어
```

---

## G. 문제 해결

### G-1. 오류 수정 요청

````text
아래 Spotfire Python 데이터 함수가 오류가 납니다. 원인과 수정된 전체 코드를 주세요.

[오류 메시지]
(전문을 그대로 붙여넣기)

[코드]
```python
(전체 코드)
```

[데이터 정보]
input.columns = [...]
input.shape = (행수, 열수)
input.dtypes = ...
````

### G-2. 결과 검증 요청

````text
아래 코드가 의도대로 동작하는지 검토해줘.
의도: [무엇을 하려는지]

```python
(코드)
```

특히 아래를 확인해줘:
1. 결측치가 있을 때 결과가 왜곡되지 않는가
2. 그룹이 1개뿐이거나 표본이 매우 적을 때 문제가 없는가
3. 0으로 나누기가 발생할 수 있는 지점이 있는가
4. 정렬이 필요한데 빠진 곳이 있는가
5. Spotfire 로 내보낼 때 문제가 될 부분(빈 결과, 전부 결측인 컬럼, 문자열 아닌 컬럼명)이 있는가
````

### G-3. 성능 개선 요청

````text
아래 코드가 100만 행에서 너무 느립니다. 결과는 동일하게 유지하면서 성능을 개선해주세요.
개선 포인트를 설명하고, 예상되는 속도 향상 정도도 알려주세요.

```python
(코드)
```
````

다음: [결과 검증하기](../03-verify/)

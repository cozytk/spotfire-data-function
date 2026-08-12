---
title: 4. 자주 나는 오류와 해결
parent: 문법
nav_order: 4
---

# 4. 자주 나는 오류와 해결
{: .no_toc }

실습 중 막히면 이 페이지에서 오류 메시지를 찾으세요.
데이터 함수에서 발생하는 문제의 대부분이 아래 10가지 안에 있습니다.
{: .fs-5 .fw-300 }

<details markdown="block">
  <summary>목차</summary>

1. TOC
{:toc}

</details>

---

## 1. `NameError: name 'input' is not defined`

**원인**: 입력 파라미터를 등록하지 않았거나, **이름 철자가 스크립트와 다릅니다.**

**해결**: 데이터 함수 편집 → 입력 파라미터 탭에서 이름을 확인하세요.
`input` / `input1` / `Input` 은 **모두 다른 이름**입니다. 대소문자까지 구분됩니다.

---

## 2. 출력 변수를 찾을 수 없음

**원인**: 출력 파라미터로 등록한 이름에 값을 **할당하지 않았습니다.**

```python
df = input
df = df.dropna()
# output = df   ← 이 줄을 빠뜨림
```

**해결**: 스크립트 **마지막에 출력 변수 할당**이 있는지 확인하세요.
조건 분기가 있다면 **모든 분기에서** 할당되어야 합니다.

```python
if len(df) == 0:
    output = pd.DataFrame([{"NOTE": "데이터 없음"}])   # 이 분기도 반드시 할당
else:
    output = df
```

---

## 3. `KeyError: 'THICKNESS'`

**원인**: 그런 컬럼이 없습니다. 대부분 아래 셋 중 하나입니다.

- **대소문자 불일치** — `Thickness` vs `THICKNESS`
- **앞뒤 공백** — `"THICKNESS "` (CSV에서 흔함)
- Table 입력에서 **일부 컬럼만 선택**해서 넘겼음

**해결**:

```python
df.columns = df.columns.str.strip()        # 컬럼명 공백 제거
print(list(df.columns))                    # 실제 컬럼명 확인 (디버깅 시)

if "THICKNESS" not in df.columns:          # 방어적 코드
    raise ValueError(f"THICKNESS 컬럼이 없습니다. 현재 컬럼: {list(df.columns)}")
```

{: .팁 }
> 마지막 방식처럼 **의미 있는 메시지와 함께 명시적으로 오류를 내면**,
> 사용자가 "무엇을 고쳐야 하는지" 바로 알 수 있습니다. 그냥 KeyError가 뜨는 것보다 훨씬 낫습니다.

---

## 4. 빈 결과 / 전부 결측인 컬럼 오류

**원인**: Spotfire는 **모든 값이 결측인 컬럼**의 타입을 결정할 수 없습니다.
필터 조건이 너무 좁아 0행이 되었을 때 자주 발생합니다.

**해결**: 빈 결과일 때 **타입에 맞는 기본값이 든 1행**을 대신 내보냅니다.

```python
if len(result) == 0:
    result = pd.DataFrame([{"EQP_ID": "NO_DATA", "N": 0, "MEAN": 0.0}])
```

[04번 예제](../../examples/04-join-and-split/)의 `safe()` 함수가 이 패턴을 일반화한 것입니다.

---

## 5. `inplace=True` 를 썼는데 값이 안 바뀜

**원인**: 최신 pandas(2.x 후반~3.x)에서 **연쇄 할당(chained assignment)** 은 원본을 바꾸지 않습니다.
경고만 뜨거나, 아무 일도 일어나지 않습니다.

```python
df['SIZE_Y'].fillna(0.1, inplace=True)      # ❌ 원본이 안 바뀔 수 있음
```

**해결**: 재할당 형태로 바꾸세요.

```python
df['SIZE_Y'] = df['SIZE_Y'].fillna(0.1)     # ✅
df = df.fillna({'SIZE_Y': 0.1})             # ✅ 여러 컬럼 한 번에
```

{: .주의 }
> 인터넷과 예전 교재에는 `inplace=True` 코드가 아주 많습니다.
> AI도 학습 데이터의 영향으로 종종 이렇게 씁니다.
> **프롬프트에 "inplace 쓰지 마"를 넣으세요.** 이 한 줄이 원인 모를 버그를 막아 줍니다.

---

## 6. `SettingWithCopyWarning`

**원인**: 필터링한 결과에 값을 대입했습니다. 그 결과가 원본의 **복사본인지 뷰인지 모호**합니다.

```python
sub = df[df["STEP_DESC"] == "PC"]
sub["FLAG"] = 1          # ⚠️ 경고
```

**해결**: 필터링 직후 `.copy()` 를 붙이는 습관을 들이세요.

```python
sub = df[df["STEP_DESC"] == "PC"].copy()
sub["FLAG"] = 1          # ✅
```

---

## 7. 조인 후 행 수가 폭증

**원인**: 오른쪽 테이블에 **조인 키가 중복**되어 있습니다. 1:N 조인이 되어 행이 곱해집니다.

**해결**: 조인 전에 반드시 확인하세요.

```python
print(lot[KEY].duplicated().sum())            # 0이어야 정상
lot = lot.drop_duplicates(subset=[KEY])       # 필요하면 정리 후 조인
```

## 8. 조인했는데 전부 결측

**원인**: 키가 매칭되지 않았습니다. 범인은 거의 항상 셋 중 하나입니다.
① 앞뒤 공백 ② 대소문자 ③ 숫자/문자 타입 불일치.

**해결**:

```python
for d in (left, right):
    d[KEY] = d[KEY].astype(str).str.strip().str.upper()

merged = left.merge(right, on=KEY, how="left", indicator=True)
print(merged["_merge"].value_counts())        # both / left_only 확인
```

---

## 9. 결과가 원본과 엉뚱하게 어긋남 (컬럼 추가 출력)

**원인**: 스크립트에서 `sort_values()` 나 `dropna()` 를 했는데
출력을 **"기존 테이블에 컬럼 추가"** 로 연결했습니다. 행 순서가 달라 엉뚱한 행에 값이 붙습니다.

**해결**: 정렬·행 삭제가 있었다면 **키 컬럼을 포함한 새 데이터 테이블로 출력**하고,
Spotfire에서 조인해서 쓰세요. 또는 마지막에 원래 순서로 되돌리세요.

```python
df = df.sort_index()          # 처리 후 원래 순서로 복귀
```

---

## 10. 실행이 매우 느림 / 멈춤

**원인과 해결**:

| 원인 | 해결 |
|---|---|
| `apply(axis=1)` 로 행마다 반복 | `np.select`, `np.where`, 벡터 연산으로 대체 (수십 배 빠름) |
| 필요 없는 컬럼까지 전부 입력 | 입력 파라미터에서 **필요한 컬럼만** 선택 |
| 전체 데이터를 매번 처리 | 입력을 **필터링으로 제한** |
| 무거운 계산인데 자동 재계산 ON | 자동 재계산 끄고 **버튼으로 실행** |
| 큰 테이블을 여러 번 `copy()` | 꼭 필요한 곳에서만 복사 |

---

## 오류가 났을 때의 순서

1. **오류 메시지의 마지막 줄**을 먼저 읽습니다. 원인이 대부분 거기 있습니다.
2. 위 목록에서 해당하는 항목을 찾습니다.
3. 없다면 **오류 메시지 전문 + 스크립트 + 입력 컬럼 목록**을 AI에게 그대로 붙여 넣고 물어보세요.

````text
아래 Spotfire Python 데이터 함수가 오류가 납니다. 원인과 수정 코드를 알려주세요.

[오류 메시지]
KeyError: 'THICKNESS'

[스크립트]
```python
(코드 전체)
```

[입력 데이터 정보]
input.columns = ['LOT_ID', 'WAFER_NO', 'Thickness', 'MEAS_TIME']
input.shape = (11091, 15)
````

{: .팁 }
> **오류 메시지를 요약하지 말고 통째로 붙여 넣으세요.**
> 사람에게는 장황해 보여도 AI에게는 그 안의 줄 번호와 타입 정보가 결정적인 단서입니다.

다음: [pandas 속성 코스](../05-pandas/)

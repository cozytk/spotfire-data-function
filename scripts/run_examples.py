"""examples/*.py 를 Spotfire 데이터 함수와 동일한 방식으로 실행해 검증합니다.

Spotfire 데이터 함수는 "입력 변수를 미리 만들어 둔 상태에서 스크립트를 실행하고,
끝난 뒤 출력 변수를 읽어 가는" 구조입니다. 이 스크립트는 그 동작을 흉내 냅니다.

  1) 예제 메타데이터의 inputs 정의대로 변수(DataFrame/스칼라)를 만든다
  2) exec() 로 예제 코드를 실행한다
  3) outputs 로 선언된 변수가 실제로 만들어졌는지, 타입이 맞는지 확인한다
  4) Spotfire 가 싫어하는 출력(빈 테이블, 전부 결측인 컬럼, list 가 든 셀 등)을 경고한다

실행:
    python scripts/run_examples.py            # 전체
    python scripts/run_examples.py 12         # 12번 예제만
"""

from __future__ import annotations

import sys
import traceback

import pandas as pd

from common import DATA, Example, load_all

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)


def build_inputs(ex: Example) -> dict:
    """메타데이터의 inputs 정의를 실제 파이썬 변수로 만든다."""
    env: dict = {}
    for name, spec in (ex.meta.get("inputs") or {}).items():
        if isinstance(spec, dict) and "file" in spec:
            df = pd.read_csv(DATA / spec["file"], encoding="utf-8-sig")
            # Spotfire 에서 '마킹/필터링으로 입력을 제한'한 상황을 흉내 내는 옵션
            if spec.get("query"):
                df = df.query(spec["query"]).reset_index(drop=True)
            if spec.get("columns"):
                df = df[spec["columns"]]
            if spec.get("column"):  # Column 타입 입력 -> pandas Series
                env[name] = df[spec["column"]]
                continue
            env[name] = df
        elif isinstance(spec, str) and spec.endswith(".csv"):
            env[name] = pd.read_csv(DATA / spec, encoding="utf-8-sig")
        else:  # Value 타입 입력 (문서 속성) -> 스칼라
            env[name] = spec
    return env


def check_output(name: str, value) -> list[str]:
    """Spotfire 로 돌려보낼 때 실제로 자주 터지는 조건들을 점검한다."""
    warn = []
    if isinstance(value, pd.DataFrame):
        if value.empty:
            warn.append(f"{name}: 빈 DataFrame — Spotfire 는 빈 결과에서 오류가 날 수 있습니다.")
        for col in value.columns:
            if not isinstance(col, str):
                warn.append(f"{name}: 컬럼명이 문자열이 아닙니다 ({col!r}) — Spotfire 는 문자열 컬럼명을 요구합니다.")
            if len(value) and value[col].isna().all():
                warn.append(f"{name}.{col}: 전체가 결측 — Spotfire 가 타입을 결정하지 못해 오류가 납니다.")
            if len(value) and value[col].map(lambda v: isinstance(v, (list, dict, set, tuple))).any():
                warn.append(f"{name}.{col}: 셀 안에 list/dict — Spotfire 로 내보낼 수 없는 타입입니다.")
    elif isinstance(value, pd.Series):
        if value.empty:
            warn.append(f"{name}: 빈 Series")
    return warn


def describe(name: str, value) -> str:
    if isinstance(value, pd.DataFrame):
        return f"{name}: DataFrame {value.shape[0]:,} rows x {value.shape[1]} cols  {list(value.columns)[:8]}"
    if isinstance(value, pd.Series):
        return f"{name}: Series len={len(value):,} dtype={value.dtype}"
    return f"{name}: {type(value).__name__} = {str(value)[:80]}"


def run(ex: Example) -> bool:
    print(f"\n{'=' * 100}\n[{ex.path.name}] {ex.title}\n{'-' * 100}")
    env = build_inputs(ex)
    for k, v in env.items():
        print("  IN   " + describe(k, v))
    try:
        exec(compile("\n" * ex.line_offset + ex.code, str(ex.path), "exec"), env, env)
    except Exception:
        print("  !! 실행 실패")
        traceback.print_exc()
        return False

    ok = True
    for name in ex.meta.get("outputs") or []:
        if name not in env:
            print(f"  !! 출력 변수 '{name}' 가 만들어지지 않았습니다.")
            ok = False
            continue
        print("  OUT  " + describe(name, env[name]))
        for w in check_output(name, env[name]):
            print("  ~~   경고: " + w)
    return ok


def main() -> int:
    picks = sys.argv[1:]
    examples = load_all()
    if picks:
        examples = [e for e in examples if any(e.path.stem.startswith(p.zfill(2)) for p in picks)]
    results = {e.path.name: run(e) for e in examples}
    failed = [k for k, v in results.items() if not v]
    print(f"\n{'=' * 100}")
    print(f"총 {len(results)}개 중 성공 {len(results) - len(failed)}개, 실패 {len(failed)}개")
    for f in failed:
        print("  실패:", f)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

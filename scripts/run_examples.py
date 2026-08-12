"""examples/*.py 를 Spotfire 데이터 함수와 동일한 방식으로 실행해 검증합니다.

Spotfire 데이터 함수는 "입력 변수를 미리 만들어 둔 상태에서 스크립트를 실행하고,
끝난 뒤 출력 변수를 읽어 가는" 구조입니다. 이 스크립트는 그 동작을 흉내 냅니다.

  1) 예제 메타데이터의 inputs 정의대로 변수(DataFrame/스칼라)를 만든다
  2) 그 입력을 **Spotfire 가 실제로 넘겨주는 dtype 으로 변환한다** (spotfire_sim)
  3) exec() 로 예제 코드를 실행한다
  4) outputs 로 선언된 변수가 실제로 만들어졌는지 확인한다
  5) 각 출력을 **실제 SBDF 로 내보내 본다** — Spotfire 가 거부하는 출력이면 여기서 똑같이 실패한다

2번이 특히 중요합니다. CSV 에서 읽은 DataFrame 과 Spotfire 가 주는 DataFrame 은 dtype 이 달라서,
`pd.read_csv()` 로만 검증하면 "로컬에서는 되는데 Spotfire 에서 터지는" 코드를 놓칩니다.

실행:
    python scripts/run_examples.py            # 전체 (Spotfire 입력 타입 재현)
    python scripts/run_examples.py 12         # 12번 예제만
    python scripts/run_examples.py --raw      # 재현 없이 CSV 원본 dtype 그대로 실행
"""

from __future__ import annotations

import sys
import traceback

import pandas as pd

from common import DATA, Example, load_all
from spotfire_sim import HAS_SPOTFIRE, check_output, to_spotfire_input

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)


def build_inputs(ex: Example, fidelity: bool = True) -> dict:
    """메타데이터의 inputs 정의를 실제 파이썬 변수로 만든다.

    ``fidelity=True`` 이면 각 테이블/컬럼 입력을 **Spotfire 가 데이터 함수에 넘겨주는
    dtype** 으로 변환한다. (시각 컬럼이 object(datetime), 정수 컬럼이 Int64 로 오는 등)
    """
    env: dict = {}
    for name, spec in (ex.meta.get("inputs") or {}).items():
        if isinstance(spec, dict) and "file" in spec:
            df = pd.read_csv(DATA / spec["file"], encoding="utf-8-sig")
            # Spotfire 에서 '마킹/필터링으로 입력을 제한'한 상황을 흉내 내는 옵션
            if spec.get("query"):
                df = df.query(spec["query"]).reset_index(drop=True)
            if spec.get("columns"):
                df = df[spec["columns"]]
            if fidelity:
                df = to_spotfire_input(df, spec.get("types"))
            if spec.get("column"):  # Column 타입 입력 -> pandas Series
                env[name] = df[spec["column"]]
                continue
            env[name] = df
        elif isinstance(spec, str) and spec.endswith(".csv"):
            df = pd.read_csv(DATA / spec, encoding="utf-8-sig")
            env[name] = to_spotfire_input(df) if fidelity else df
        else:  # Value 타입 입력 (문서 속성) -> 스칼라
            env[name] = spec
    return env


def describe(name: str, value) -> str:
    if isinstance(value, pd.DataFrame):
        return f"{name}: DataFrame {value.shape[0]:,} rows x {value.shape[1]} cols  {list(value.columns)[:8]}"
    if isinstance(value, pd.Series):
        return f"{name}: Series len={len(value):,} dtype={value.dtype}"
    return f"{name}: {type(value).__name__} = {str(value)[:80]}"


def run(ex: Example, fidelity: bool = True) -> bool:
    print(f"\n{'=' * 100}\n[{ex.path.name}] {ex.title}\n{'-' * 100}")
    env = build_inputs(ex, fidelity=fidelity)
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
        errors, warnings = check_output(name, env[name])
        for w in warnings:
            print("  ~~   경고: " + w)
        for e in errors:
            print("  !!   출력 거부: " + e)
            ok = False
    return ok


def main() -> int:
    args = sys.argv[1:]
    fidelity = "--raw" not in args
    picks = [a for a in args if not a.startswith("-")]

    examples = load_all()
    if picks:
        examples = [e for e in examples if any(e.path.stem.startswith(p.zfill(2)) for p in picks)]

    mode = "Spotfire 입력 타입 재현" if fidelity else "CSV 원본 dtype (--raw)"
    sbdf_mode = "실제 SBDF 내보내기로 검증" if HAS_SPOTFIRE else "규칙 기반 점검 (pip install spotfire 권장)"
    print(f"입력 모드: {mode}\n출력 검증: {sbdf_mode}")

    results = {e.path.name: run(e, fidelity=fidelity) for e in examples}
    failed = [k for k, v in results.items() if not v]
    print(f"\n{'=' * 100}")
    print(f"총 {len(results)}개 중 성공 {len(results) - len(failed)}개, 실패 {len(failed)}개")
    for f in failed:
        print("  실패:", f)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

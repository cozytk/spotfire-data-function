"""Spotfire 데이터 함수의 **입력/출력 규약**을 로컬에서 그대로 재현한다.

`run_examples.py` 가 예제를 그냥 `pd.read_csv()` 로 읽어서 실행하면
"로컬에서는 되는데 Spotfire에 붙여 넣으면 터지는" 코드를 걸러내지 못합니다.
CSV 에서 읽은 DataFrame 과 Spotfire 가 실제로 건네주는 DataFrame 은 **dtype 이 다르기** 때문입니다.

    CSV        : MEAS_TIME -> object(str)      "2026-03-02 06:04:42"
    Spotfire   : MEAS_TIME -> object(datetime) datetime.datetime(2026, 3, 2, 6, 4, 42)
                              ^^^^^^ datetime64 가 아니라 object! -> .dt 접근자가 실패한다

이 모듈은 두 가지를 제공합니다.

1. :func:`to_spotfire_input`
   CSV 로 읽은 DataFrame 을 **Spotfire 가 데이터 함수에 넘겨주는 것과 동일한 dtype** 으로 바꾼다.
2. :func:`check_output`
   출력 변수를 **실제 SBDF 로 내보내 본다.** Spotfire 가 거부하는 출력이면 여기서 똑같이 실패한다.

공식 `spotfire` 패키지(`pip install spotfire`)가 설치되어 있으면 실제 SBDF 왕복으로
검증하므로 재현도가 가장 높고, 없으면 동등한 dtype 변환으로 대체합니다.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import tempfile
import warnings as warnings_module
from decimal import Decimal

import numpy as np
import pandas as pd

try:  # 공식 패키지가 있으면 진짜 SBDF 로 검증한다
    import spotfire
    from spotfire import sbdf

    HAS_SPOTFIRE = True
except ImportError:  # pragma: no cover - 설치되지 않은 환경
    spotfire = None
    sbdf = None
    HAS_SPOTFIRE = False


# Spotfire 데이터 타입 이름 (spotfire.sbdf 가 인정하는 이름과 동일)
SPOTFIRE_TYPES = (
    "Boolean", "Integer", "LongInteger", "SingleReal", "Real",
    "DateTime", "Date", "Time", "TimeSpan", "String", "Binary", "Currency",
)

# Spotfire 타입 -> 데이터 함수 안에서 실제로 보게 되는 pandas dtype
#   (spotfire.sbdf 왕복으로 실측한 결과. docs/syntax/03-datatypes.md 의 표와 같은 내용)
INPUT_DTYPE = {
    "Boolean": "object",      # 셀 값은 bool
    "Integer": "Int32",       # nullable, 결측은 pd.NA
    "LongInteger": "Int64",   # nullable, 결측은 pd.NA
    "SingleReal": "float32",
    "Real": "float64",
    "DateTime": "object",     # 셀 값은 datetime.datetime  <- datetime64 아님
    "Date": "object",         # 셀 값은 datetime.date
    "Time": "object",         # 셀 값은 datetime.time
    "TimeSpan": "object",     # 셀 값은 datetime.timedelta
    "String": "object",
    "Binary": "object",
    "Currency": "object",     # 셀 값은 decimal.Decimal
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$")
_BOOL_VALUES = {"TRUE", "FALSE"}


def infer_spotfire_type(series: pd.Series) -> str:
    """CSV 컬럼 하나가 Spotfire 로 임포트되면 어떤 타입이 될지 추정한다.

    Spotfire 의 CSV 임포트 타입 추론과 같은 방침이다.
    확실할 때만 특수 타입으로 보고, 애매하면 String 으로 둔다.
    """
    s = series.dropna()
    if s.empty:
        return "String"
    if pd.api.types.is_bool_dtype(series):
        return "Boolean"
    if pd.api.types.is_integer_dtype(series):
        return "LongInteger"
    if pd.api.types.is_float_dtype(series):
        # 결측 때문에 float 이 된 정수 컬럼도 Spotfire 에서는 Real 로 들어온다
        return "Real"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "DateTime"

    text = s.astype(str)
    if text.str.upper().isin(_BOOL_VALUES).all():
        return "Boolean"
    if text.map(lambda v: bool(_DATETIME_RE.match(v))).all():
        return "DateTime"
    if text.map(lambda v: bool(_DATE_RE.match(v))).all():
        return "Date"
    return "String"


def _as_spotfire_dtype(series: pd.Series, sf_type: str) -> pd.Series:
    """컬럼 하나를 해당 Spotfire 타입이 데이터 함수에 도착했을 때의 모습으로 바꾼다."""
    na = series.isna()

    if sf_type == "Boolean":
        if pd.api.types.is_bool_dtype(series):
            out = series.astype(object)
        else:
            out = series.astype(str).str.upper().map({"TRUE": True, "FALSE": False}).astype(object)
    elif sf_type in ("Integer", "LongInteger"):
        out = pd.to_numeric(series, errors="coerce").astype(INPUT_DTYPE[sf_type])
    elif sf_type in ("Real", "SingleReal"):
        out = pd.to_numeric(series, errors="coerce").astype(INPUT_DTYPE[sf_type])
    elif sf_type == "DateTime":
        parsed = pd.to_datetime(series, errors="coerce")
        out = pd.Series([v.to_pydatetime() if pd.notna(v) else None for v in parsed],
                        index=series.index, dtype=object)
    elif sf_type == "Date":
        parsed = pd.to_datetime(series, errors="coerce")
        out = pd.Series([v.date() if pd.notna(v) else None for v in parsed], index=series.index, dtype=object)
    elif sf_type == "Time":
        parsed = pd.to_datetime(series, errors="coerce")
        out = pd.Series([v.time() if pd.notna(v) else None for v in parsed], index=series.index, dtype=object)
    elif sf_type == "TimeSpan":
        parsed = pd.to_timedelta(series, errors="coerce")
        out = pd.Series([v.to_pytimedelta() if pd.notna(v) else None for v in parsed],
                        index=series.index, dtype=object)
    elif sf_type == "Currency":
        out = pd.Series([Decimal(str(v)) if pd.notna(v) else None for v in series],
                        index=series.index, dtype=object)
    else:  # String / Binary
        out = pd.Series([None if pd.isna(v) else str(v) for v in series], index=series.index, dtype=object)

    # 결측은 Spotfire 가 주는 형태로 되돌린다 (숫자형만 NaN/NA, 나머지는 None)
    if sf_type in ("Boolean", "DateTime", "Date", "Time", "TimeSpan", "String", "Binary", "Currency"):
        out = out.where(~na, None)
    return out


def to_spotfire_input(df: pd.DataFrame, types: dict[str, str] | None = None) -> pd.DataFrame:
    """CSV 로 읽은 DataFrame 을 **Spotfire 가 데이터 함수에 넘겨주는 모습**으로 바꾼다.

    :param df: ``pd.read_csv()`` 등으로 읽은 원본
    :param types: 컬럼별 Spotfire 타입을 직접 지정 (미지정 컬럼은 자동 추론)
    :returns: dtype 이 Spotfire 와 동일하게 맞춰진 새 DataFrame
    """
    types = dict(types or {})
    out = pd.DataFrame(index=df.index)
    for col in df.columns:
        sf_type = types.get(col) or infer_spotfire_type(df[col])
        if sf_type not in INPUT_DTYPE:
            raise ValueError(f"알 수 없는 Spotfire 타입 '{sf_type}' (컬럼 {col})")
        out[col] = _as_spotfire_dtype(df[col], sf_type)
    return out


def spotfire_types_of(df: pd.DataFrame) -> dict[str, str]:
    """DataFrame 각 컬럼이 Spotfire 로 나갈 때 어떤 타입이 되는지 조사한다."""
    if not (HAS_SPOTFIRE and isinstance(df, pd.DataFrame) and len(df.columns)):
        return {}
    path = tempfile.mktemp(suffix=".sbdf")
    try:
        sbdf.export_data(df, path)
        back = sbdf.import_data(path)
        return {c: t for c, t in spotfire.get_spotfire_types(back).items()}
    except Exception:
        return {}
    finally:
        if os.path.exists(path):
            os.remove(path)


# 실제 SBDF 오류 메시지 -> 사람이 읽을 수 있는 원인/해결 안내
_ERROR_HINTS = (
    ("all values are missing",
     "전부 결측인 컬럼입니다. 결측을 채우거나 컬럼을 빼거나, "
     "spotfire.set_spotfire_types() 로 타입을 직접 지정하세요."),
    ("unknown type",
     "셀 안에 Spotfire 로 내보낼 수 없는 값(list/dict/set 등)이 있습니다. "
     "문자열로 합치거나(join) 행으로 펼치세요(explode)."),
    ("do not match",
     "한 컬럼에 서로 다른 타입이 섞여 있습니다. astype() 으로 통일하세요."),
    ("unique column names",
     "컬럼명이 중복입니다. merge 의 suffixes 나 rename 으로 구분하세요."),
    ("No objects to concatenate",
     "컬럼이 하나도 없는 DataFrame 입니다. 최소 1개 컬럼이 있어야 합니다."),
)


# 출력 변수에 넣을 수 있는 파이썬 타입 (DataFrame 이 아니면 1컬럼 표로 감싸서 내보낸다)
_EXPORTABLE = (pd.DataFrame, pd.Series, np.ndarray, list, str, bytes, int, float, bool,
               _dt.date, _dt.time, _dt.timedelta, Decimal)


def _is_figure(value) -> bool:
    """matplotlib Figure 인지 (import 하지 않고 판별). Figure 는 Binary 로 내보내진다."""
    return type(value).__module__.startswith("matplotlib.") and type(value).__name__ == "Figure"


def _hint_for(message: str) -> str:
    for needle, hint in _ERROR_HINTS:
        if needle in message:
            return hint
    return "Spotfire 로 내보낼 수 없는 출력입니다."


def check_output(name: str, value) -> tuple[list[str], list[str]]:
    """출력 변수를 Spotfire 로 실제로 내보내 보고 (오류, 경고) 를 돌려준다.

    `spotfire` 패키지가 있으면 진짜 SBDF 로 써 보므로 Spotfire 와 동일하게 실패한다.
    없으면 규칙 기반 점검으로 대체한다.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if isinstance(value, pd.DataFrame):
        for col in value.columns:
            if not isinstance(col, str):
                errors.append(f"{name}: 컬럼명이 문자열이 아닙니다 ({col!r}) — "
                              f"pv.columns = [str(c) for c in pv.columns] 로 문자열화하세요.")
        if isinstance(value.index, pd.MultiIndex) or value.index.name is not None:
            warnings.append(f"{name}: 인덱스에 이름이 있습니다(index.name={value.index.name!r}) — "
                            f"인덱스는 Spotfire 로 전달되지 않습니다. reset_index() 를 확인하세요.")
    if isinstance(value, pd.Series) and value.index.name is not None:
        warnings.append(f"{name}: Series 의 인덱스({value.index.name!r})는 Spotfire 로 전달되지 않습니다. "
                        f"reset_index() 로 컬럼으로 만드세요.")

    if HAS_SPOTFIRE:
        path = tempfile.mktemp(suffix=".sbdf")
        try:
            with warnings_module.catch_warnings():
                warnings_module.simplefilter("ignore", FutureWarning)
                sbdf.export_data(value, path, default_column_name=name)
        except Exception as exc:  # SBDFError 등
            errors.append(f"{name}: SBDF 내보내기 실패 — {type(exc).__name__}: {exc}\n"
                          f"           → {_hint_for(str(exc))}")
        finally:
            if os.path.exists(path):
                os.remove(path)
    else:
        # 공식 패키지가 없을 때의 대체 점검
        if not isinstance(value, _EXPORTABLE) and not _is_figure(value):
            warnings.append(f"{name}: {type(value).__name__} 타입 — Spotfire 로 내보낼 수 있는지 확인이 필요합니다.")
        if isinstance(value, pd.DataFrame):
            if value.empty and not len(value.columns):
                errors.append(f"{name}: 컬럼이 없는 빈 DataFrame 입니다.")
            for col in value.columns:
                if len(value) and value[col].isna().all():
                    errors.append(f"{name}.{col}: 전체가 결측 — Spotfire 가 타입을 결정하지 못합니다.")
                if len(value) and value[col].map(lambda v: isinstance(v, (list, dict, set, tuple))).any():
                    errors.append(f"{name}.{col}: 셀 안에 list/dict — 내보낼 수 없는 타입입니다.")

    return errors, warnings

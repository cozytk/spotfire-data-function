"""예제 파일(examples/*.py)의 공통 파싱 유틸리티.

각 예제 파일은 아래 구조를 따릅니다.

    '''---
    title: 예제 제목
    ... (YAML 메타데이터) ...
    ---
    ## 시나리오
    (마크다운 설명 본문)
    '''
    import pandas as pd
    ...

즉 **모듈 docstring 하나**에 메타데이터 + 교안 본문이 들어 있고,
그 아래가 Spotfire에 그대로 붙여 넣을 수 있는 실제 스크립트입니다.
이 파일을 파싱해서 (1) 로컬 실행 검증(run_examples.py)과
(2) 교안 문서 생성(build_docs.py)에 함께 사용합니다.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
DATA = ROOT / "data"


@dataclass
class Example:
    path: Path
    meta: dict
    body_md: str
    code: str
    slug: str = ""
    line_offset: int = 0
    outputs: list = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.meta.get("title", self.path.stem)

    @property
    def number(self) -> int:
        return int(self.path.stem.split("_")[0])


def parse(path: Path) -> Example:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    doc = ast.get_docstring(tree, clean=False) or ""
    m = re.match(r"\s*---\n(.*?)\n---\n(.*)", doc, re.S)
    if not m:
        raise ValueError(f"{path.name}: '---' 메타데이터 블록을 찾을 수 없습니다.")
    meta = yaml.safe_load(m.group(1)) or {}
    body_md = m.group(2).strip("\n")

    # 모듈 docstring 이후가 실제 코드
    first_stmt = tree.body[0]
    end = getattr(first_stmt, "end_lineno", 1)
    lines = src.splitlines()
    start = end  # docstring 다음 줄(0-based)
    while start < len(lines) and not lines[start].strip():
        start += 1
    code = "\n".join(lines[start:]).rstrip("\n")
    slug = path.stem.replace("_", "-")
    # 실행 시 오류 메시지의 줄 번호를 원본 파일과 일치시키기 위한 오프셋
    return Example(path=path, meta=meta, body_md=body_md, code=code, slug=slug, line_offset=start)


def load_all() -> list[Example]:
    return [parse(p) for p in sorted(EXAMPLES.glob("[0-9][0-9]_*.py"))]

"""examples/*.py 로부터 교안의 '예제' 페이지(docs/examples/*.md)를 생성합니다.

예제 파일 하나가 (설명 + 실행 가능한 코드 + 메타데이터)의 단일 원본이고,
이 스크립트가 그것을 교안 페이지로 옮깁니다. 설명과 코드가 어긋날 일이 없습니다.

실행: python scripts/build_docs.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

from common import ROOT, load_all

DOCS = ROOT / "docs"
OUT = DOCS / "examples"
REPO = "https://github.com/cozytk/spotfire-data-function"

LEVEL_NAMES = {
    1: "Level 1 · 정제 기초",
    2: "Level 2 · 재구조화",
    3: "Level 3 · 시계열과 공정 분석",
    4: "Level 4 · 통계·자동화·Spotfire 고유 기능",
}


def io_table(ex) -> str:
    """입력/출력 파라미터 요약 표."""
    lines = ["| 구분 | 이름 | 타입 | 연결 |", "|---|---|---|---|"]
    for name, spec in (ex.meta.get("inputs") or {}).items():
        if isinstance(spec, dict) and "file" in spec:
            kind = "Column" if spec.get("column") else "Table"
            src = f"`{spec['file']}`"
            if spec.get("query"):
                src += " (마킹/필터로 제한)"
        elif isinstance(spec, str) and spec.endswith(".csv"):
            kind, src = "Table", f"`{spec}`"
        else:
            kind = "Value"
            src = f"문서 속성 (예: `{spec}`)"
        lines.append(f"| 입력 | `{name}` | {kind} | {src} |")
    for name in ex.meta.get("outputs") or []:
        lines.append(f"| 출력 | `{name}` | Table | 새 데이터 테이블 |")
    return "\n".join(lines)


def render(ex, nav_order: int) -> str:
    body = ex.body_md
    code_block = "```python\n" + ex.code + "\n```"
    if "{{CODE}}" in body:
        body = body.replace("{{CODE}}", code_block)
    else:
        body = body + "\n\n## 스크립트\n\n" + code_block

    pkgs = ex.meta.get("packages") or []
    pkg_note = (
        f"\n> **추가 패키지 필요**: `{'`, `'.join(pkgs)}` — `도구 > Python 도구 > 패키지 관리` 에서 설치\n"
        if pkgs
        else ""
    )
    data_files = ex.meta.get("data") or []
    data_links = ", ".join(f"[`{d}`]({REPO}/blob/main/data/{d})" for d in data_files)

    # 제목에 따옴표·콜론이 들어가도 깨지지 않도록 YAML 로 직렬화한다
    front_matter = yaml.safe_dump(
        {"title": f"{ex.number:02d}. {ex.title}", "parent": "예제 모음", "nav_order": nav_order},
        allow_unicode=True,
        sort_keys=False,
    ).strip()

    head = f"""---
{front_matter}
---

# {ex.number:02d}. {ex.title}
{{: .no_toc }}

**난이도** {ex.meta.get('difficulty', '')} · **{LEVEL_NAMES.get(ex.meta.get('level', 1), '')}**

{ex.meta.get('summary', '')}
{pkg_note}
사용 데이터: {data_links or '-'} · [스크립트 원본]({REPO}/blob/main/examples/{ex.path.name})

<details markdown="block">
  <summary>목차</summary>

1. TOC
{{:toc}}

</details>

### 파라미터 요약
{{: .no_toc }}

{io_table(ex)}

---

"""
    return head + body + "\n"


def render_index(examples) -> str:
    rows = ["| # | 예제 | 난이도 | 무엇을 배우나 |", "|---|---|---|---|"]
    by_level: dict[int, list] = {}
    for ex in examples:
        by_level.setdefault(ex.meta.get("level", 1), []).append(ex)

    sections = []
    for level in sorted(by_level):
        sections.append(f"\n## {LEVEL_NAMES.get(level, level)}\n")
        sections.append("| # | 예제 | 난이도 | 무엇을 배우나 |")
        sections.append("|---|---|---|---|")
        for ex in by_level[level]:
            sections.append(
                f"| {ex.number:02d} | [{ex.title}](./{ex.slug}/) "
                f"| {ex.meta.get('difficulty', '')} | {ex.meta.get('summary', '')} |"
            )
    del rows

    return f"""---
title: 예제 모음
nav_order: 4
has_children: true
---

# 예제 모음
{{: .no_toc }}

모든 예제는 **실제로 실행해 검증한 코드**입니다.
`data/` 폴더의 CSV를 Spotfire에 불러온 뒤 스크립트를 그대로 붙여 넣으면 동작합니다.

각 예제는 같은 형식으로 되어 있습니다.

1. **시나리오** — 어떤 업무 상황인가
2. **왜 Spotfire 기본 기능으로는 어려운가** — 데이터 함수를 쓸 이유
3. **데이터 함수 설정** — 입력/출력 파라미터를 어떻게 잡을 것인가
4. **스크립트** — 붙여 넣어 바로 쓰는 코드
5. **핵심 포인트** — 코드에서 반드시 이해하고 넘어갈 것
6. **이렇게 물어보세요** — 같은 결과를 AI에게 얻어내는 프롬프트
7. **확인 & 응용** — 검증 방법과 다음 과제

{"".join(s + chr(10) for s in sections)}

---

## 난이도 표기

| 표기 | 의미 |
|---|---|
| ★☆☆ | pandas를 처음 봐도 따라갈 수 있음 |
| ★★☆ | 함수 하나의 동작을 이해해야 함 |
| ★★★ | 여러 개념이 조합됨 — 프롬프트로 얻고 검증하는 연습에 적합 |
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.md"):
        stale.unlink()

    examples = load_all()
    for i, ex in enumerate(examples, start=1):
        (OUT / f"{ex.slug}.md").write_text(render(ex, i), encoding="utf-8")
    (OUT / "index.md").write_text(render_index(examples), encoding="utf-8")
    print(f"생성 완료: {len(examples)}개 예제 페이지 + 목차 → {OUT}")


if __name__ == "__main__":
    main()

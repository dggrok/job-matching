"""教育部专业目录解析:把 pdftotext 得到的文本解析成结构化节点。

数据源(已放入 catalogs/source/):
- undergrad-2025.txt:《普通高等学校本科专业目录(2025 年)》
- graduate-2022.txt:《研究生教育学科专业目录(2022 年)》

节点结构:
{
  "id":     "UG:080701",        # 命名空间:层次 + 代码,避免本科专业类与研究生一级学科(同为 4 位)冲突
  "level":  "UG" | "PG",
  "kind":   "category" | "class" | "major" | "discipline",
  "code":   "080701",
  "name":   "电子信息工程",
  "parent": "UG:0807" | None,
  "note":   "可授工学或理学学士学位" | None,
  "professional": bool           # 仅研究生:专业学位类别(代码第三位 >= 5)
}
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

Node = dict[str, Any]

# 本科:门类行 "  01    学科门类:哲学"
_UG_CATEGORY = re.compile(r"^\s*(\d{2})\s+学科门类[:：]\s*(\S+)\s*$")
# 本科:专业类行 "0101           哲学类"
_UG_CLASS = re.compile(r"^\s*(\d{4})\s+(\S+类)\s*$")
# 本科:专业行 "010103K         宗教学" / "080911TK   网络空间安全"
_UG_MAJOR = re.compile(r"^\s*(\d{6}[A-Z]{0,2})\s+(\S.*?)\s*$")
# 名称后的括号注释 "(注:可授经济学或管理学学士学位)"
_NOTE = re.compile(r"[（(]注[:：]\s*(.*?)[）)]\s*$")

# 研究生:门类行 "   01 哲学" / "   03    法学"
_PG_CATEGORY = re.compile(r"^\s*(\d{2})\s+(\S+)\s*$")
# 研究生:一级学科/专业学位类别行 "0101   哲学" / "0251   金融*"
_PG_DISCIPLINE = re.compile(r"^\s*(\d{4})\s+(\S.*?)\s*$")
# 页码行 "— 47 —" / "—1—"
_PAGE_NO = re.compile(r"^\s*—\s*\d+\s*—\s*$")


def _clean_name(raw: str) -> tuple[str, str | None]:
    """拆出名称与括号注释。"""
    note = None
    m = _NOTE.search(raw)
    if m:
        note = m.group(1).strip()
        raw = raw[: m.start()].strip()
    return raw.strip(), note


def parse_undergrad(text: str) -> list[Node]:
    """解析本科专业目录文本。"""
    nodes: list[Node] = []
    category: str | None = None
    cls: str | None = None
    started = False
    for line in text.splitlines():
        if _PAGE_NO.match(line) or not line.strip():
            continue
        m = _UG_CATEGORY.match(line)
        if m:
            started = True
            code, name = m.groups()
            category = f"UG:{code}"
            cls = None
            nodes.append(_node("UG", "category", code, name, None))
            continue
        if not started:
            continue  # 跳过"说明"部分
        m = _UG_CLASS.match(line)
        if m and category:
            code, name = m.groups()
            cls = f"UG:{code}"
            nodes.append(_node("UG", "class", code, name, category))
            continue
        m = _UG_MAJOR.match(line)
        if m and cls:
            code, raw_name = m.groups()
            name, note = _clean_name(raw_name)
            nodes.append(_node("UG", "major", code, name, cls, note=note))
    return nodes


def parse_graduate(text: str) -> list[Node]:
    """解析研究生学科专业目录文本。"""
    nodes: list[Node] = []
    category: str | None = None
    started = False
    for line in text.splitlines():
        if _PAGE_NO.match(line) or not line.strip():
            continue
        # 门类行:两位数字 + 名称;必须先于一级学科判断,且只在 "说明" 之后生效
        m = _PG_CATEGORY.match(line)
        if m:
            code, name = m.groups()
            if not started and code != "01":
                continue
            started = True
            category = f"PG:{code}"
            nodes.append(_node("PG", "category", code, name, None))
            continue
        if not started:
            continue
        m = _PG_DISCIPLINE.match(line)
        if m and category:
            code, raw_name = m.groups()
            professional = int(code[2]) >= 5
            star = raw_name.endswith("*")
            raw_name = raw_name.rstrip("*").strip()
            name, note = _clean_name_pg(raw_name)
            node = _node("PG", "discipline", code, name, category, note=note)
            node["professional"] = professional
            node["masterOnly"] = star
            nodes.append(node)
    return nodes


def _clean_name_pg(raw: str) -> tuple[str, str | None]:
    """研究生名称如 "心理学(可授教育学、理学学位)",括号内容作为注释。"""
    m = re.search(r"[（(](可授.*?)[）)]\s*$", raw)
    if m:
        return raw[: m.start()].strip(), m.group(1).strip()
    return raw.strip(), None


def _node(
    level: str,
    kind: str,
    code: str,
    name: str,
    parent: str | None,
    note: str | None = None,
) -> Node:
    return {
        "id": f"{level}:{code}",
        "level": level,
        "kind": kind,
        "code": code,
        "name": name,
        "parent": parent,
        "note": note,
    }


def load_catalogs(source_dir: Path) -> dict[str, list[Node]]:
    """读取 catalogs/source 下的文本并解析。"""
    ug = parse_undergrad((source_dir / "undergrad-2025.txt").read_text(encoding="utf-8"))
    pg = parse_graduate((source_dir / "graduate-2022.txt").read_text(encoding="utf-8"))
    return {"UG": ug, "PG": pg}

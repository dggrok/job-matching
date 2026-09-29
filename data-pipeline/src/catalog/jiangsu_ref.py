"""江苏省《考试录用公务员专业参考目录》解析。

江苏职位表的「专业」列大量使用该目录里的自定义「专业大类」(如「法律类」「财务财会类」「中文文秘类」),
它们不是国家专业目录里的类,必须靠这份目录才能知道每个大类包含哪些研究生/本科专业。

官方发布的是 Word 文档(.doc)。本模块读取它的纯文本导出(UTF-8):
    macOS:  textutil -convert txt -encoding UTF-8 xxx.doc -output catalogs/source/jiangsu-2026-major-ref.txt
    其他系统: 用 Word / WPS 另存为「纯文本」,编码选 UTF-8。

文本结构(每个专业大类):
    序号(纯数字一行)
    专业大类名称
    研究生专业列表(一行,逗号分隔)
    本科专业列表
    专科专业列表(个别大类没有)
"""

from __future__ import annotations

import re
from pathlib import Path

from ..normalize.shengkao import split_top_level

Ref = dict[str, dict[str, list[str]]]  # 大类名 → {"PG": [...], "UG": [...], "ZK": [...]}

_PAGE_MARK = re.compile(r"^[—\-–\s]*PAGE\b.*$", re.I)


def parse_ref_text(content: str) -> Ref:
    lines = [ln.strip() for ln in content.splitlines()]
    try:
        start = next(i for i, ln in enumerate(lines) if ln == "专业大类")
    except StopIteration:
        raise ValueError("找不到表头「专业大类」,请确认文本来自《专业参考目录》") from None
    nz = [ln for ln in lines[start + 1 :] if ln and not _PAGE_MARK.match(ln)]

    cats: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(nz):
        if nz[i].isdigit() and i + 1 < len(nz) and not nz[i + 1].isdigit():
            name = nz[i + 1]
            i += 2
            # 名称被换行拆成两行的情况(如「仪表仪器及」/「测试技术类」)
            if not name.endswith("类") and i < len(nz) and nz[i].endswith("类") and len(nz[i]) <= 8:
                name += nz[i]
                i += 1
            cats.append((name, []))
            continue
        if cats:
            cats[-1][1].append(nz[i])
        i += 1

    ref: Ref = {}
    for name, cols in cats:
        if not cols:
            raise ValueError(f"专业大类「{name}」下没有专业列表")
        levels = ["PG", "UG", "ZK"]
        ref[name] = {lv: split_top_level(col, "，,") for lv, col in zip(levels, cols)}
    if len(ref) < 30:
        raise ValueError(f"只解析出 {len(ref)} 个专业大类,远少于预期,文本格式可能变了")
    return ref


def load_ref(path: Path) -> Ref:
    return parse_ref_text(path.read_text(encoding="utf-8"))

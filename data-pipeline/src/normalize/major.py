"""职位表「专业」字段解析:自由文本 → 结构化专业要求。

输出结构(majorRule):
{
  "unlimited": bool,                 # 专业不限
  "segments": [                      # 按学历层次分段
    {"level": "UG" | "PG" | "ANY",   # ANY 表示未标注学历层次,或写明"本科或研究生"
     "tokens": [Token, ...]}
  ],
  "warnings": [str, ...]             # 解析告警
}

Token:
{
  "raw": "0812计算机科学与技术(限软件方向)",
  "name": "计算机科学与技术",
  "codes": ["0812"],
  "refs": ["PG:0812"],               # 命中的目录节点 id,可能同时含 UG 与 PG
  "partial": bool,                   # 仅通过二级学科/专业学位方向代码前缀命中,需人工确认
  "resolved": bool,                  # 是否在目录里找到了对应节点
  "qualifiers": [                    # 括号里的附加限定
     {"kind": "exclude", "text": "...", "refs": ["UG:030102T", ...]},
     {"kind": "restrict", "text": "限会计学"}
  ]
}

匹配语义(由前端引擎实现):用户专业的 id 链(专业 → 专业类 → 门类)与 refs 有交集即命中;
命中的 token 若带 restrict 限定、或 partial 为 true,则结果降级为「待确认」;
命中 exclude 限定所列专业则判为不符合。
"""

from __future__ import annotations

import re
from typing import Any

from ..catalog.index import CatalogIndex, digits_of, norm_name

Token = dict[str, Any]

_PAREN = re.compile(r"[\uff08(][^\uff08(\uff09)]*[\uff09)]")
_PLACEHOLDER = re.compile(r"\u00a7(\d+)\u00a7")

# 学历层次标记。注意长的写在前面。
_LEVEL_MARK = re.compile(
    r"(?:以)?(?:大学)?"
    r"(本科或硕士研究生|本科或研究生|本科及研究生|本科生|本科|专科|大专"
    r"|硕士研究生及以上|硕士研究生|博士研究生|研究生)"
    r"(?:招收|专业报考|专业为|专业)?(?:为)?\s*[:\uff1a]?"
)
_SEPS = re.compile(r"[\u3001,\uff0c;\uff1b\u3002/]+")
_LEAD_JUNK = re.compile(r"^(?:或者|或|及|和|与|以及|专业为|专业|须为|为)+")
_TRAIL_JUNK = re.compile(r"(?:等相关专业|等专业|等)$")
_CODE_HEAD = re.compile(r"^(\d{2,6}[A-Z]{0,2})\s*(.*)$")
_CODE_TAIL = re.compile(r"^(.*?[\u4e00-\u9fff])(\d{4,6}[A-Z]{0,2})$")
_CODE_ONLY = re.compile(r"^\d{2,6}[A-Z]{0,2}(?:(?:或|、|,|\uff0c|/|和)\d{2,6}[A-Z]{0,2})*$")
_CODE_FIND = re.compile(r"\d{2,6}[A-Z]{0,2}")
_EXCLUDE_HEAD = re.compile(r"^(?:不含|不包含|不包括|除)")
_INFO_HEAD = re.compile(r"^(?:以上|均为|含|包括|包含|即|指|注|如|例如|统称|学科门类|专业类|一级学科|为)")


def _mask(text: str) -> tuple[str, list[str]]:
    """把括号内容替换成占位符,保证后续按分隔符切分时不会切进括号里。"""
    store: list[str] = []

    def repl(m: re.Match[str]) -> str:
        store.append(m.group(0))
        return f"\u00a7{len(store) - 1}\u00a7"

    prev = None
    while prev != text:
        prev = text
        text = _PAREN.sub(repl, text)
    return text, store


def _unmask(text: str, store: list[str]) -> str:
    prev = None
    while prev != text:
        prev = text
        text = _PLACEHOLDER.sub(lambda m: store[int(m.group(1))], text)
    return text


def _level_of(marker: str) -> str:
    if ("本科" in marker or "专科" in marker or "大专" in marker) and (
        "研究生" in marker
    ):
        return "ANY"
    if "研究生" in marker or "硕士" in marker or "博士" in marker:
        return "PG"
    return "UG"


def split_segments(masked: str) -> list[tuple[str, str]]:
    """按学历层次标记切段,返回 [(level, 内容)]。"""
    marks = list(_LEVEL_MARK.finditer(masked))
    segs: list[tuple[str, str]] = []
    head_end = marks[0].start() if marks else len(masked)
    head = masked[:head_end].strip(" \u3001,\uff0c;\uff1b\u3002")
    if head:
        segs.append(("ANY", head))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(masked)
        content = masked[m.end() : end].strip(" \u3001,\uff0c;\uff1b\u3002")
        if content:
            segs.append((_level_of(m.group(1)), content))
    return segs


class MajorParser:
    def __init__(self, index: CatalogIndex):
        self.index = index

    # ---------- 对外入口 ----------
    def parse(self, text: str) -> dict[str, Any]:
        raw = (text or "").strip().replace("\n", "\uff1b")
        rule: dict[str, Any] = {"unlimited": False, "segments": [], "warnings": []}
        if not raw:
            rule["warnings"].append("专业为空")
            return rule
        masked, store = _mask(raw)
        if re.search(r"不限", masked):
            rule["unlimited"] = True
            return rule
        for level, content in split_segments(masked):
            tokens = []
            for part in _SEPS.split(content):
                part = _LEAD_JUNK.sub("", part.strip())
                part = _TRAIL_JUNK.sub("", part).strip()
                if not part:
                    continue
                tokens.append(self._parse_token(_unmask(part, store), level))
            if tokens:
                rule["segments"].append({"level": level, "tokens": tokens})
        if not rule["segments"]:
            rule["warnings"].append("专业无法切分出有效条目")
        return rule

    # ---------- token ----------
    def _parse_token(self, raw: str, seg_level: str) -> Token:
        masked, store = _mask(raw)
        m = _CODE_HEAD.match(masked.strip())
        codes: list[str] = []
        if m:
            codes.append(m.group(1))
            base = m.group(2)
        else:
            base = masked.strip()
            # 名称后紧跟代码,如 "计算机类0809"
            t = _CODE_TAIL.match(base)
            if t:
                base, tail_code = t.group(1), t.group(2)
                codes.append(tail_code)

        qualifiers: list[dict[str, Any]] = []
        raw_quals: list[str] = []
        for ph in _PLACEHOLDER.finditer(base):
            inner = _unmask(store[int(ph.group(1))], store)
            raw_quals.append(inner[1:-1].strip())
        name = _PLACEHOLDER.sub("", base).strip()
        name = _unmask(name, store)

        levels = {"UG": ["UG"], "PG": ["PG"], "ANY": ["UG", "PG"]}[seg_level]
        suffix_xue = False
        for q in raw_quals:
            if not q:
                continue
            if q == "学":
                suffix_xue = True
            elif _CODE_ONLY.match(q):
                codes.extend(_CODE_FIND.findall(q))
            elif _EXCLUDE_HEAD.match(q):
                qualifiers.append(
                    {"kind": "exclude", "text": q, "refs": self._resolve_names(q, levels)}
                )
            elif _INFO_HEAD.match(q):
                continue  # 说明性文字,不影响匹配
            else:
                qualifiers.append({"kind": "restrict", "text": q})

        refs, partial = self._resolve(name, codes, levels, suffix_xue)
        token: Token = {
            "raw": raw.strip(),
            "name": name,
            "codes": codes,
            "refs": refs,
            "partial": partial,
            "resolved": bool(refs),
            "qualifiers": qualifiers,
        }
        if not refs:
            token["likelyLevel"] = self._guess_level(name, seg_level)
        return token

    @staticmethod
    def _guess_level(name: str, seg_level: str) -> str:
        """未能解析的条目大概率属于哪个学历层次(启发式,仅用于降低"待确认"噪音)。

        - 明确标了本科或研究生的段,直接沿用;
        - 未标层次的段:名称以"类/相关专业/门类"结尾的多为本科口径的分类,
          其余(如 民商法学、植物病理学 这类二级学科名)多为研究生口径。
        """
        if seg_level in ("UG", "PG"):
            return seg_level
        if re.search(r"(类|相关专业|门类)$", name):
            return "UG"
        return "PG"

    # ---------- 解析为目录节点 ----------
    def _resolve(
        self, name: str, codes: list[str], levels: list[str], suffix_xue: bool
    ) -> tuple[list[str], bool]:
        refs: list[str] = []
        partial = False
        nname = norm_name(name)

        for code in codes:
            digits = digits_of(code)
            for lv in levels:
                node = self.index.by_code(lv, code)
                if node and (not nname or self._name_compatible(nname, node["name"])):
                    self._add(refs, node["id"])
                    continue
                # 研究生二级学科 / 专业学位方向:代码前 4 位归到一级学科,标为待确认
                if lv == "PG" and len(digits) >= 5:
                    parent = self.index.by_code("PG", digits[:4])
                    if parent:
                        self._add(refs, parent["id"])
                        partial = True
                # 6 位数字码在 ANY 段里常是研究生二级学科,名称对不上时不当本科专业
        if refs:
            return refs, partial

        # "工学门类" / "法学门类":只在学科门类里找
        if nname.endswith("门类"):
            for lv in levels:
                for node in self.index.find_category_by_name(lv, nname[:-2]):
                    self._add(refs, node["id"])
            if refs:
                return refs, partial

        # 无代码或代码没命中:按名称
        candidates = [nname]
        if suffix_xue:
            candidates.insert(0, nname + "\u5b66")
        if nname.endswith("\u4e13\u4e1a"):
            candidates.append(nname[:-2])
        for cand in candidates:
            if not cand:
                continue
            for lv in levels:
                for node in self.index.find_by_name(lv, cand):
                    self._add(refs, node["id"])
                    if self.index.is_alias(lv, cand):
                        partial = True  # 别名是推断映射,降级为待确认
            if refs:
                break
        if refs:
            return refs, partial

        # 回退:招录机关常把目录名后面加一个"类"(如 会计学类、软件工程类),
        # 去掉"类"再查一次;这是推断,命中后降级为待确认。
        if nname.endswith("\u7c7b") and len(nname) > 2:
            for lv in levels:
                for node in self.index.find_by_name(lv, nname[:-1]):
                    self._add(refs, node["id"])
            if refs:
                partial = True
        return refs, partial

    def _resolve_names(self, text: str, levels: list[str]) -> list[str]:
        """解析 "不含知识产权、监狱学…专业" 里列出的专业名。"""
        body = _EXCLUDE_HEAD.sub("", text)
        body = re.sub(r"(?:等)?(?:专业|外)+$", "", body.strip())
        refs: list[str] = []
        for part in _SEPS.split(body):
            part = re.sub(r"^(?:及|和|与)", "", part.strip())
            part = re.sub(r"(?:专业|等)$", "", part)
            if not part:
                continue
            for lv in levels:
                for node in self.index.find_by_name(lv, part):
                    self._add(refs, node["id"])
        return refs

    @staticmethod
    def _name_compatible(a: str, b: str) -> bool:
        b = norm_name(b)
        return a == b or a in b or b in a

    @staticmethod
    def _add(lst: list[str], value: str) -> None:
        if value not in lst:
            lst.append(value)

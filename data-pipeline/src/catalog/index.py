"""专业目录索引:名称与代码的双向查找,并区分本科(UG)与研究生(PG)命名空间。"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from .parse import Node

# 名称查找时的优先级:同名时优先取最具体的层级,避免 "法学" 既命中专业又命中门类。
_KIND_PRIORITY = ["major", "class", "discipline", "category"]

_SPACE = re.compile(r"\s+")


def norm_name(name: str) -> str:
    """名称归一:去空白、统一括号、去 * 标记。"""
    name = _SPACE.sub("", name)
    # 全角括号统一成半角
    name = name.replace("\uff08", "(").replace("\uff09", ")")
    return name.rstrip("*")


def digits_of(code: str) -> str:
    """去掉专业代码里的 K/T/TK 后缀,只保留数字。"""
    return re.sub(r"[A-Za-z]+$", "", code)


class CatalogIndex:
    def __init__(self, catalogs: dict[str, list[Node]], aliases: dict | None = None):
        self.nodes: dict[str, Node] = {}
        self._by_digits: dict[str, dict[str, Node]] = {"UG": {}, "PG": {}}
        self._by_name: dict[str, dict[str, list[Node]]] = {
            "UG": defaultdict(list),
            "PG": defaultdict(list),
        }
        for level, nodes in catalogs.items():
            for n in nodes:
                self.nodes[n["id"]] = n
                self._by_digits[level][digits_of(n["code"])] = n
                self._by_name[level][norm_name(n["name"])].append(n)
        # 人工别名:{"UG": {"别名": "节点id" 或 ["节点id", ...]}, "PG": {...}}
        self._alias: dict[str, dict[str, list[str]]] = {"UG": {}, "PG": {}}
        for level, mapping in (aliases or {}).items():
            for alias, target in (mapping or {}).items():
                ids = [target] if isinstance(target, str) else list(target)
                self._alias[level][norm_name(alias)] = ids

    # ---- 基础查找 ----
    def get(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def by_code(self, level: str, code: str) -> Node | None:
        """按代码精确查找(忽略 K/T 后缀)。"""
        return self._by_digits[level].get(digits_of(code))

    def find_by_name(self, level: str, name: str) -> list[Node]:
        """按名称查找,只返回优先级最高那一种层级的节点。"""
        key = norm_name(name)
        targets = [t for t in self._alias[level].get(key, []) if t in self.nodes]
        if targets:
            return [self.nodes[t] for t in targets]
        hits = self._by_name[level].get(key, [])
        if not hits:
            return []
        for kind in _KIND_PRIORITY:
            picked = [n for n in hits if n["kind"] == kind]
            if picked:
                return picked
        return hits

    def is_alias(self, level: str, name: str) -> bool:
        """该名称是否来自人工别名表(推断映射,需降级为待确认)。"""
        return norm_name(name) in self._alias[level]

    def find_category_by_name(self, level: str, name: str) -> list[Node]:
        """只在学科门类里按名称查找(用于 "工学门类" 这类写法)。"""
        key = norm_name(name)
        return [n for n in self._by_name[level].get(key, []) if n["kind"] == "category"]

    # ---- 层级关系 ----
    def chain(self, node_id: str) -> list[str]:
        """返回从自身到门类的 id 链,如 UG:080701 → UG:0807 → UG:08。"""
        out: list[str] = []
        cur: str | None = node_id
        while cur:
            out.append(cur)
            node = self.nodes.get(cur)
            cur = node["parent"] if node else None
        return out

    def children(self, node_id: str) -> list[Node]:
        return [n for n in self.nodes.values() if n["parent"] == node_id]

    def names_under(self, node_id: str) -> Iterable[str]:
        return (n["name"] for n in self.children(node_id))

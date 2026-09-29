"""省考(浙江、江苏)共用的标准化工具。

各省职位表的列名、取值写法都不同,但落到同一份 Position 契约上需要的换算是相通的:
学历/学位层次、中文数字、职位属性等。省内特有的解析放在 zhejiang.py / jiangsu.py。
"""

from __future__ import annotations

import re
from typing import Any

from .remark import extract_remark

_CN_NUM = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

ALL_EDU = ["大专", "本科", "硕士", "博士"]

# 省考职位表出现过的「学历要求」写法 → 允许的最高学历层次(按最高学历判断)
EDU_MAP: dict[str, list[str]] = {
    "高中（中专）及以上": ALL_EDU,  # 面向优秀村干部/书记的职位,学历放宽,系统只区分大专起
    "专科及以上": ALL_EDU,
    "大专及以上": ALL_EDU,
    "本科及以上": ["本科", "硕士", "博士"],
    "本科": ["本科"],
    "硕士研究生及以上": ["硕士", "博士"],
    "研究生": ["硕士", "博士"],
    "硕士研究生": ["硕士"],
    "博士研究生": ["博士"],
    "博士": ["博士"],
}

# 省考职位表出现过的「学位要求」写法(浙江单独一列;江苏在「其它」里,由 jiangsu.py 解析)
DEGREE_MAP: dict[str, str] = {
    "不限": "none",
    "学士及以上": "bachelor",
    "硕士及以上": "master",
    "博士": "doctor",
}


def cn_to_int(s: str) -> int | None:
    """「两/二/2」→ 2;不认识返回 None。"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    return _CN_NUM.get(s)


def normalize_edu(value: str, warnings: list[str]) -> list[str]:
    key = (value or "").strip()
    if key in EDU_MAP:
        return list(EDU_MAP[key])
    warnings.append(f"未识别的学历要求:{key!r}")
    return []


def split_top_level(text: str, seps: str = "，,、；;") -> list[str]:
    """按分隔符切分,但括号内的分隔符不切(如「民商法学(含:劳动法学、社会保障法学)」)。"""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in text:
        if ch in "（(":
            depth += 1
        elif ch in "）)":
            depth = max(0, depth - 1)
        if ch in seps and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


_ENGLISH = re.compile(r"大学英语|英语专业|英语[四六八]级|雅思|托福|四级|六级|CET", re.I)


def extract_common_remark(remark: str) -> dict[str, Any]:
    """省考备注的通用抽取:复用国考的 extract_remark,但去掉不适用于省考的部分。

    - 英语要求:国考固定为 425 分线,省考写法各异(如「四级500分或六级450分」),
      不能套用等级换算,改为把相关句子收进 notes,由用户核对;
    - 年龄:省考的年龄在专门的列/条款里,备注里的年龄不再单独抽取。
    """
    rr = extract_remark(remark)
    rr["cet"] = None
    rr["cetAltAllowed"] = False
    rr["maxAge"] = None
    rr["ageRelaxedTo"] = None
    notes = [s for s in _sentences(remark) if _ENGLISH.search(s)]
    if notes:
        rr["notes"] = notes
    return rr


def _sentences(text: str) -> list[str]:
    from .remark import split_sentences

    return split_sentences(text)


def sparse(rr: dict[str, Any]) -> dict[str, Any]:
    """去掉假值,控制 JSON 体积。"""
    return {k: v for k, v in rr.items() if v not in (False, None, [], {}, "")}

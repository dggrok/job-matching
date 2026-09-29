"""学历、学位、政治面貌、基层经历等结构化字段的归一。

这些字段在国考职位表里是有限枚举,可以完全结构化;遇到未知取值会返回告警,而不是静默丢弃。
"""

from __future__ import annotations

# 学历层次:大专 < 本科 < 硕士 < 博士
EDU_ORDER = ["大专", "本科", "硕士", "博士"]

_EDU_MAP: dict[str, list[str]] = {
    "大专及以上": ["大专", "本科", "硕士", "博士"],
    "大专或本科": ["大专", "本科"],
    "仅限大专": ["大专"],
    "本科及以上": ["本科", "硕士", "博士"],
    "仅限本科": ["本科"],
    "本科或硕士研究生": ["本科", "硕士"],
    "硕士研究生及以上": ["硕士", "博士"],
    "仅限硕士研究生": ["硕士"],
    "仅限博士研究生": ["博士"],
}

_DEGREE_MAP = {
    "与最高学历相对应的学位": "matchHighest",
    "学士": "bachelor",
    "硕士": "master",
    "博士": "doctor",
    "无要求": "none",
}

_POLITICAL_MAP = {
    "不限": "any",
    "中共党员": "party",
    "中共党员或共青团员": "partyOrLeague",
}

_GRASSROOTS_MAP = {
    "无限制": 0,
    "一年": 1,
    "二年": 2,
    "三年": 3,
    "四年": 4,
    "五年以上": 5,
}

# 服务基层项目:规范名称 → 标识
PROJECT_KEYS: dict[str, str] = {
    "大学生村官": "village",
    "农村义务教育阶段学校教师特设岗位计划": "teacher",
    "“三支一扶”计划": "sanzhi",
    "大学生志愿服务西部计划": "west",
    "在军队服役5年（含）以上的高校毕业生退役士兵": "veteran",
    # 以下三项仅省考使用(国考职位表不会出现),标识需与前端 PROJECT_LABELS 保持一致
    "大学生志愿服务山区、海岛、边远地区计划": "shanhai",
    "“志愿服务乡村振兴计划”（含原“苏北计划”）": "rural",
    "安排工作的退役军士和义务兵": "soldier",
}


def normalize_education(value: str, warnings: list[str]) -> list[str]:
    """返回该职位允许的学历层次列表(按最高学历判断)。"""
    key = (value or "").strip()
    if key in _EDU_MAP:
        return _EDU_MAP[key]
    warnings.append(f"未识别的学历要求:{key!r}")
    return []


def normalize_degree(value: str, warnings: list[str]) -> str:
    key = (value or "").strip()
    if key in _DEGREE_MAP:
        return _DEGREE_MAP[key]
    warnings.append(f"未识别的学位要求:{key!r}")
    return "unknown"


def normalize_political(value: str, warnings: list[str]) -> str:
    key = (value or "").strip()
    if key in _POLITICAL_MAP:
        return _POLITICAL_MAP[key]
    warnings.append(f"未识别的政治面貌:{key!r}")
    return "unknown"


def normalize_grassroots_years(value: str, warnings: list[str]) -> int:
    key = (value or "").strip()
    if key in _GRASSROOTS_MAP:
        return _GRASSROOTS_MAP[key]
    warnings.append(f"未识别的基层工作年限:{key!r}")
    return 0


def normalize_projects(value: str, warnings: list[str]) -> list[str]:
    """把 "大学生村官、“三支一扶”计划、..." 拆成项目标识列表;无限制返回空列表。"""
    key = (value or "").strip()
    if not key or key == "无限制":
        return []
    found: list[str] = []
    rest = key
    for name, ident in PROJECT_KEYS.items():
        if name in rest:
            found.append(ident)
            rest = rest.replace(name, "")
    # 去掉分隔符后如果还有残留文字,说明出现了没见过的项目
    leftover = rest.replace("、", "").replace("，", "").replace(",", "").strip()
    if leftover:
        warnings.append(f"服务基层项目含未识别内容:{leftover!r}")
    return found

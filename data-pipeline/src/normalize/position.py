"""把一行原始职位数据标准化为前端消费的 Position。

字段约定见 方案文档「B. 数据契约」。为控制体积:
- majorRule 按专业原文去重,放在 majorRules 表里,职位只保存 majorId;
- remarkRules 只保留有值的字段(稀疏对象);
- 不保存 27 列原始数据的完整副本,只保留展示和匹配需要的字段;
- 年龄界限不逐职位保存:公告级年龄规则放在 manifest 的 ageRule 里,
  前端结合 police 标记与 rr.maxAge / rr.ageRelaxedTo 计算。
"""

from __future__ import annotations

from typing import Any

from .education import (
    normalize_degree,
    normalize_education,
    normalize_grassroots_years,
    normalize_political,
    normalize_projects,
)
from .major import MajorParser
from .remark import extract_remark

Position = dict[str, Any]


def text(v: Any) -> str:
    """单元格转字符串;整数型浮点去掉小数点。"""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def to_int(v: Any, warnings: list[str], field: str) -> int:
    s = text(v)
    try:
        return int(float(s))
    except ValueError:
        warnings.append(f"{field}不是数字:{s!r}")
        return 0


class MajorTable:
    """按专业原文去重的专业规则表。"""

    def __init__(self, parser: MajorParser):
        self.parser = parser
        self.rules: dict[str, dict[str, Any]] = {}
        self._by_text: dict[str, str] = {}

    def register(self, raw_text: str) -> str:
        key = raw_text.strip()
        if key in self._by_text:
            return self._by_text[key]
        mid = f"m{len(self._by_text)}"
        rule = self.parser.parse(key)
        rule["text"] = key
        self.rules[mid] = rule
        self._by_text[key] = mid
        return mid


def build_position(
    exam_id: str,
    cfg: dict[str, Any],
    raw: dict[str, Any],
    majors: MajorTable,
) -> Position:
    warnings: list[str] = []
    dept_code = text(raw.get("部门代码"))
    code = text(raw.get("职位代码"))

    edu = normalize_education(text(raw.get("学历")), warnings)
    degree = normalize_degree(text(raw.get("学位")), warnings)
    political = normalize_political(text(raw.get("政治面貌")), warnings)
    grassroots = normalize_grassroots_years(text(raw.get("基层工作最低年限")), warnings)
    projects = normalize_projects(text(raw.get("服务基层项目工作经历")), warnings)

    remark_raw = text(raw.get("备注"))
    rr_full = extract_remark(remark_raw)
    # 稀疏化:去掉假值
    rr = {k: v for k, v in rr_full.items() if v not in (False, None, [], {})}

    attr = text(raw.get("职位属性"))
    org_level = text(raw.get("机构层级"))
    police = attr == "公安机关人民警察职位" and org_level in ("市（地）级", "县（区）级及以下")

    major_text = text(raw.get("专业"))
    major_id = majors.register(major_text)
    if majors.rules[major_id]["warnings"]:
        warnings.extend(majors.rules[major_id]["warnings"])

    phones = [text(raw.get(k)) for k in ("咨询电话1", "咨询电话2", "咨询电话3")]

    pos: Position = {
        "id": f"{exam_id}:{dept_code}:{code}",
        "code": code,
        "deptCode": dept_code,
        "org": text(raw.get("部门名称")),
        "unit": text(raw.get("用人司局")),
        "orgType": text(raw.get("机构性质")),
        "orgLevel": org_level,
        "title": text(raw.get("招考职位")),
        "examCategory": text(raw.get("考试类别")),
        "attr": attr,
        "dist": text(raw.get("职位分布")),
        "intro": text(raw.get("职位简介")),
        "headcount": to_int(raw.get("招考人数"), warnings, "招考人数"),
        "location": text(raw.get("工作地点")),
        "hukou": text(raw.get("落户地点")),
        "edu": edu,
        "eduText": text(raw.get("学历")),
        "degree": degree,
        "political": political,
        "grassroots": grassroots,
        "projects": projects,
        "majorId": major_id,
        "remark": remark_raw,
        "rr": rr,
        "interviewRatio": text(raw.get("面试人员比例")),
        "skillTest": text(raw.get("是否在面试阶段组织专业能力测试")),
        "site": text(raw.get("部门网站")),
        "phones": [p for p in phones if p],
        "sheet": text(raw.get("_sheet")),
    }
    if police:
        pos["police"] = True
    if warnings:
        pos["warnings"] = warnings
    return pos

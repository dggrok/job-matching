"""浙江省考职位表 → 标准 Position。

官方《招考计划一览表》(xlsx)的列(以 2026 年度为准,已实测):
招录单位名称、职位代码、职位名称、职位属性、职位大类、职位小类、招录人数、咨询电话、职位简介、
学历要求、学位要求、现有身份要求、政治面貌要求、民族要求、年龄要求、专业要求、
是否加试心理测评/体能测评/专业、备注。

与国考的主要差异:
- 年龄写在每个职位上(18-38 / 18-30 / 18-35 / 18-28 / 18-43 ...),不能只用公告级规则;
- 「现有身份要求」把应届、基层年限、服务基层项目、优秀村干部等混在一列,需要拆开;
- 专业写成「研究生所学专业要求为:… ;本科所学专业要求为:…」,归一后交给同一个专业解析器;
- 表里没有工作地点,只能从招录单位名称推断所在地市。
"""

from __future__ import annotations

import re
from typing import Any

from .position import MajorTable, Position, text, to_int
from .shengkao import DEGREE_MAP, cn_to_int, extract_common_remark, normalize_edu, sparse

# 县级行政区 → 地市。招录单位名称常只写县(市)名,不带地市名,需要这张表推断所在地。
COUNTY_TO_CITY: dict[str, str] = {}
for _city, _counties in {
    "杭州市": "萧山 余杭 富阳 临安 临平 钱塘 滨江 西湖 拱墅 上城 桐庐 淳安 建德",
    "宁波市": "海曙 江北 镇海 北仑 鄞州 奉化 余姚 慈溪 宁海 象山",
    "温州市": "鹿城 龙湾 瓯海 洞头 瑞安 乐清 龙港 永嘉 平阳 苍南 文成 泰顺",
    "嘉兴市": "南湖 秀洲 嘉善 海盐 海宁 平湖 桐乡",
    "湖州市": "吴兴 南浔 德清 长兴 安吉",
    "绍兴市": "越城 柯桥 上虞 诸暨 嵊州 新昌",
    "金华市": "婺城 金东 兰溪 义乌 东阳 永康 武义 浦江 磐安",
    "衢州市": "柯城 衢江 江山 常山 开化 龙游",
    "舟山市": "定海 普陀 岱山 嵊泗",
    "台州市": "椒江 黄岩 路桥 临海 温岭 玉环 三门 天台 仙居",
    "丽水市": "莲都 龙泉 青田 缙云 遂昌 松阳 云和 庆元 景宁",
}.items():
    for _c in _counties.split():
        COUNTY_TO_CITY[_c] = _city

CITIES = list(dict.fromkeys(COUNTY_TO_CITY.values()))
_CITY_KEYS = [c[:-1] for c in CITIES]  # 杭州、宁波……
# 县名按长度降序,避免「临安」被「安」之类短词抢先命中(名称都是 2 字,这里主要是稳妥)
_COUNTY_KEYS = sorted(COUNTY_TO_CITY, key=len, reverse=True)
_PREFIX = re.compile(r"^(?:中共|中国共产党|中国共产主义青年团|共青团|政协|浙江省)+")


def infer_region(org: str) -> str:
    """从招录单位名称推断所在地:「省级」或某地市;推断不出来返回空串。"""
    name = org.strip()
    # 「浙江省××厅/局/中心」是省级机关;「浙江诸暨经济开发区」不以「浙江省」开头,不在此列
    if name.startswith(("浙江省", "浙江警察学院")):
        return "省级"
    head = _PREFIX.sub("", name)[:10]
    for key in _CITY_KEYS:
        if head.startswith(key):
            return key + "市"
    for county in _COUNTY_KEYS:
        if head.startswith(county):
            return COUNTY_TO_CITY[county]
    # 兜底:名称前 12 字里出现地市名/县名
    window = name[:12]
    for key in _CITY_KEYS:
        if key in window:
            return key + "市"
    for county in _COUNTY_KEYS:
        if county in window:
            return COUNTY_TO_CITY[county]
    return ""


# ---------------- 现有身份要求 ----------------

_FRESH = re.compile(r"^(\d{4})年应届毕业生$")
_GRASSROOTS = re.compile(r"^([一二两三四五六七八九十\d]+)年以上基层工作经历$")


def parse_identity(value: str, warnings: list[str]) -> dict[str, Any]:
    """拆解「现有身份要求」。返回 {freshOnly, gradYear, grassroots, projects, altIdentity, identity}。"""
    v = (value or "").strip()
    out: dict[str, Any] = {}
    if v in ("", "不限"):
        return out
    m = _FRESH.match(v)
    if m:
        out["freshOnly"] = True
        out["gradYear"] = int(m.group(1))
        return out
    m = _GRASSROOTS.match(v)
    if m:
        years = cn_to_int(m.group(1))
        if years is None:
            warnings.append(f"未识别的现有身份要求:{v!r}")
        else:
            out["grassroots"] = years
        return out
    if v in ("优秀村干部", "优秀社区干部"):
        out["identity"] = [f"限{v}"]
        return out
    # 面向服务基层项目人员(含退役军人、退役军士和义务兵、山区海岛县乡镇事业编制人员)
    projects: list[str] = []
    if "服务基层项目人员" in v:
        projects += ["west", "shanhai", "sanzhi"]
    if "在军队服役满5年的高校毕业生退役军人" in v:
        projects.append("veteran")
    if "退役军士和义务兵" in v and (projects or v.startswith("符合条件的具有本科以上学历安排工作的")):
        projects.append("soldier")
    if projects:
        out["projects"] = projects
        if "乡镇事业编制人员" in v:
            out["altIdentity"] = "符合条件的山区海岛县乡镇事业编制人员(具体由各市公告明确)"
        return out
    if "退役军人" in v or "人武学院" in v:
        out["identity"] = [f"限{v}"]
        return out
    warnings.append(f"未识别的现有身份要求:{v!r}")
    return out


# ---------------- 年龄要求 ----------------

_AGE_STD = re.compile(r"^年龄要求(\d+)至(\d+)周岁(?:（(\d{4})年硕士以上应届毕业生放宽至(\d+)周岁）)?$")
_AGE_VILLAGE = re.compile(r"^年龄要求现任村“两委”正职(\d+)至(\d+)周岁（非现任村“两委”正职(\d+)至(\d+)周岁.*）$")


def parse_age(value: str, warnings: list[str]) -> dict[str, int]:
    """返回 {ageMin, ageMax, ageMaxFresh?, ageRelaxedTo?}(单位:周岁)。"""
    v = (value or "").strip().replace("\u3000", "").replace(" ", "")
    m = _AGE_STD.match(v)
    if m:
        out = {"ageMin": int(m.group(1)), "ageMax": int(m.group(2))}
        out["ageMaxFresh"] = int(m.group(4)) if m.group(4) else out["ageMax"]
        return out
    m = _AGE_VILLAGE.match(v)
    if m:
        # 现任村「两委」正职可到 43 周岁(需身份核对),其他人 38 周岁
        return {
            "ageMin": int(m.group(3)),
            "ageMax": int(m.group(4)),
            "ageMaxFresh": int(m.group(4)),
            "ageRelaxedTo": int(m.group(2)),
        }
    warnings.append(f"未识别的年龄要求:{v!r}")
    return {}


# ---------------- 专业 ----------------

_MAJOR_LEAD = re.compile(r"(研究生|本科|专科|大专)所学专业要求为[:：]")


def normalize_major_text(value: str) -> str:
    """「研究生所学专业要求为:A、B;本科所学专业要求为:C」→「研究生:A、B;本科:C」,交给通用专业解析器。"""
    return _MAJOR_LEAD.sub(lambda m: f"{m.group(1)}：", (value or "").strip())


# ---------------- 主入口 ----------------


def build_position(exam_id: str, cfg: dict[str, Any], raw: dict[str, Any], majors: MajorTable) -> Position:
    warnings: list[str] = []
    code = text(raw.get("职位代码"))
    dept_code = code[:8]
    org = text(raw.get("招录单位名称"))

    edu = normalize_edu(text(raw.get("学历要求")), warnings)
    degree_text = text(raw.get("学位要求"))
    degree = DEGREE_MAP.get(degree_text)
    if degree is None:
        warnings.append(f"未识别的学位要求:{degree_text!r}")
        degree = "unknown"

    political_text = text(raw.get("政治面貌要求"))
    political = {"不限": "any", "中共党员": "party"}.get(political_text)
    if political is None:
        warnings.append(f"未识别的政治面貌:{political_text!r}")
        political = "unknown"

    identity_text = text(raw.get("现有身份要求"))
    ident = parse_identity(identity_text, warnings)
    age_text = text(raw.get("年龄要求"))
    age = parse_age(age_text, warnings)

    remark = text(raw.get("备注"))
    rr = extract_common_remark(remark)
    for k in ("freshOnly", "gradYear", "altIdentity"):
        if k in ident:
            rr[k] = ident[k]
    if ident.get("identity"):
        rr["identity"] = list(ident["identity"])
    ethnic = text(raw.get("民族要求"))
    if ethnic and ethnic != "不限":
        rr.setdefault("identity", []).append(ethnic)
    if "ageRelaxedTo" in age:
        rr["ageRelaxedTo"] = age["ageRelaxedTo"]

    major_id = majors.register(normalize_major_text(text(raw.get("专业要求"))))
    if majors.rules[major_id]["warnings"]:
        warnings.extend(majors.rules[major_id]["warnings"])

    rule = cfg["ageRule"]
    extras: list[list[str]] = []
    for label, key in (("现有身份要求", "现有身份要求"), ("年龄要求", "年龄要求"), ("学位要求", "学位要求"), ("民族要求", "民族要求")):
        val = text(raw.get(key))
        if val and val != "不限":
            extras.append([label, val])
    tests = [name for name, key in (("心理测评", "是否加试心理测评"), ("体能测评", "是否加试体能测评"), ("专业加试", "是否加试专业")) if text(raw.get(key)) == "是"]
    if tests:
        extras.append(["加试项目", "、".join(tests)])

    pos: Position = {
        "id": f"{exam_id}:{dept_code}:{code}",
        "code": code,
        "deptCode": dept_code,
        "org": org,
        "unit": "",
        "orgType": "",
        "orgLevel": "",
        "title": text(raw.get("职位名称")),
        "examCategory": text(raw.get("职位大类")),
        "attr": text(raw.get("职位属性")),
        "dist": text(raw.get("职位小类")),
        "intro": text(raw.get("职位简介")),
        "headcount": to_int(raw.get("招录人数"), warnings, "招考人数"),
        "location": infer_region(org),
        "hukou": "",
        "edu": edu,
        "eduText": text(raw.get("学历要求")),
        "degree": degree,
        "political": political,
        "grassroots": ident.get("grassroots", 0),
        "projects": ident.get("projects", []),
        "majorId": major_id,
        "remark": remark,
        "rr": sparse(rr),
        "interviewRatio": "",
        "skillTest": "加试专业" if "专业加试" in tests else "",
        "site": "",
        "phones": [p for p in [text(raw.get("咨询电话"))] if p],
        "sheet": text(raw.get("_sheet")),
    }
    # 年龄:只有与公告级默认值不同的职位才单独存,控制体积
    if age:
        if age["ageMin"] != rule["minAge"]:
            pos["ageMin"] = age["ageMin"]
        if age["ageMax"] != rule["maxAge"] or age["ageMaxFresh"] != rule["maxAgeFreshPg"]:
            pos["ageMax"] = age["ageMax"]
            pos["ageMaxFresh"] = age["ageMaxFresh"]
    if extras:
        pos["extras"] = extras
    if not pos["location"]:
        warnings.append("无法从招录单位名称推断所在地")
    if warnings:
        pos["warnings"] = warnings
    return pos

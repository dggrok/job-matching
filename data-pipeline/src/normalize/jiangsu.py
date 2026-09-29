"""江苏省考职位表 → 标准 Position。

官方《考录职位简介表》共 16 份 xls(省级机关、13 个设区市、地方统计系统、监狱戒毒系统),
每份一个 Sheet、14 列:隶属关系、地区代码、地区名称、单位代码、单位名称、职位代码、职位名称、
职位简介、考试类别(A/B/C)、开考比例、招考人数、学历、专业、其它。

与国考、浙江的主要差异:
1. 学位、政治面貌、性别、应届、基层经历、户籍、证书等条件全都挤在「其它」一列里,
   用逗号分隔成一个个短句,这里逐句归类;认不出的硬条件句放进 notes(待确认),不会被当成"没有要求"。
2. 「专业」列使用江苏自己的《专业参考目录》里的专业大类(法律类、财务财会类……),
   由 JiangsuMajorTable 用参考目录展开成国家专业目录的节点集合(见 catRefs)。
3. 职位代码(两位)有分组含义(60-69 面向应届生、90-96 面向服务基层项目人员……),
   分组的说明取自当年公告,配置在 exams.yaml 的 codeGroups 里,每年必须核对。
"""

from __future__ import annotations

import re
from typing import Any

from ..catalog.index import CatalogIndex
from ..catalog.jiangsu_ref import Ref
from .major import MajorParser
from .position import MajorTable, Position, text, to_int
from .shengkao import cn_to_int, normalize_edu, sparse, split_top_level

_ORG_LEVEL = {"省": "省级", "市": "市级", "县": "县(区)级", "乡镇": "乡镇(街道)", "垂直": "省以下垂直管理"}

_POLICE_HINT = re.compile(r"公安|监狱|戒毒|司法警察|法警")

# ---------------- 专业 ----------------


class JiangsuMajorTable(MajorTable):
    """把「财务财会类,审计类,会计学」这样的江苏专业写法转成标准 majorRule。

    - 专业大类:用《专业参考目录》展开为国家目录节点集合,统一放在 cat_refs,
      规则里只放一个 {cat: 大类名} 的引用 token(否则每条规则都要重复几百个 id,体积会爆炸);
    - 其他专业名称:交给通用的 MajorParser(命中目录的自动关联,目录外的标为未解析)。
    """

    def __init__(self, parser: MajorParser, ref: Ref, index: CatalogIndex):
        super().__init__(parser)
        self.ref = ref
        self.index = index
        self.cat_refs: dict[str, list[str]] = {}

    def _resolve_names(self, level: str, names: list[str]) -> list[str]:
        ids: list[str] = []
        for name in names:
            variants = [name]
            base = re.sub(r"[（(].*?[）)]", "", name).strip()
            if base and base != name:
                variants.append(base)
            for v in variants:
                hits = [n for n in self.index.find_by_name(level, v) if n["kind"] in ("major", "discipline", "class")]
                for n in hits:
                    if n["id"] not in ids:
                        ids.append(n["id"])
                if hits:
                    break
        return ids

    def refs_of(self, cat: str) -> list[str]:
        if cat not in self.cat_refs:
            entry = self.ref[cat]
            ids = self._resolve_names("PG", entry.get("PG", [])) + self._resolve_names("UG", entry.get("UG", []))
            self.cat_refs[cat] = ids
        return self.cat_refs[cat]

    def register(self, raw_text: str) -> str:
        key = raw_text.strip()
        if key in self._by_text:
            return self._by_text[key]
        rule = self._build_rule(key)
        rule["text"] = key
        mid = f"m{len(self._by_text)}"
        self.rules[mid] = rule
        self._by_text[key] = mid
        return mid

    def _build_rule(self, key: str) -> dict[str, Any]:
        if not key:
            return {"unlimited": False, "segments": [], "warnings": ["专业为空"]}
        if "不限" in key:
            return {"unlimited": True, "segments": [], "warnings": []}
        parts = split_top_level(key)
        cats = [p for p in parts if p in self.ref]
        loose = [p for p in parts if p not in self.ref]
        rule: dict[str, Any]
        if loose:
            rule = self.parser.parse("，".join(loose))
        else:
            rule = {"unlimited": False, "segments": [], "warnings": []}
        if cats:
            cat_tokens = []
            for c in dict.fromkeys(cats):
                self.refs_of(c)
                cat_tokens.append(
                    {"raw": c, "name": c, "codes": [], "refs": [], "cat": c,
                     "partial": False, "resolved": True, "qualifiers": []}
                )
            any_seg = next((s for s in rule["segments"] if s["level"] == "ANY"), None)
            if any_seg is None:
                rule["segments"].append({"level": "ANY", "tokens": cat_tokens})
            else:
                any_seg["tokens"].extend(cat_tokens)
            rule["warnings"] = [w for w in rule["warnings"] if w != "专业无法切分出有效条目"]
        return rule


# ---------------- 「其它」列 ----------------

_DEGREE = re.compile(r"取得相应(博士|硕士|学士)?学位")
_YEARS = re.compile(r"([一二两三四五六七八九十\d]+)年以上基层工作经历")
_AGE_MAX = re.compile(r"年龄不超过(\d+)周岁|(\d+)周岁以下")
_AGE_RELAX = re.compile(r"年龄可放宽至(\d+)周岁")
_FRESH = re.compile(r"面向(\d{4})年普通高校应届毕业生")
_STAGE = re.compile(r"本科阶段|本科为|研究生学历报考|研究生报考|研究生阶段|以研究生学历|本科、研究生")
_ENGLISH = re.compile(r"大学英语|英语专业|英语[四六八]级|雅思|托福|四级|六级")
_INFO = re.compile(
    r"视力|色盲|色弱|身高|体测|体能|裸眼|适合|生活能够自理|能正常履行|独立开展|加班|值夜班|夜间|高空|现场|一线|"
    r"出差|异地|总成绩计算|面试阶段|试讲|危险"
)
_HARD = re.compile(r"须|必须|具有|取得|限|曾|毕业|专业|资格|经历|年龄|党员|团员|发表|获得")


def parse_other(value: str, warnings: list[str]) -> dict[str, Any]:
    """逐句归类「其它」列。返回字段:
    degree / political / grassroots / gender / rr(dict,含 notes、residency 等)。
    """
    out: dict[str, Any] = {"degree": "none", "political": "any", "grassroots": 0}
    rr: dict[str, Any] = {}
    notes: list[str] = []
    residency: list[str] = []
    certificates: list[str] = []
    work: list[str] = []
    ug_stage: list[str] = []
    identity: list[str] = []

    for c in [x.strip() for x in re.split(r"[，,；;。]", value or "") if x.strip()]:
        m = _DEGREE.search(c)
        if m and len(c) <= 14:
            out["degree"] = {"博士": "doctor", "硕士": "master", "学士": "bachelor"}.get(m.group(1), "matchHighest")
            continue
        if c in ("男性", "女性") or c in ("限男性", "限女性"):
            rr["gender"] = "male" if "男" in c else "female"
            continue
        m = _FRESH.search(c)
        if m:
            rr["freshOnly"] = True
            rr["gradYear"] = int(m.group(1))
            continue
        if "党员" in c or "团员" in c:
            if "团员" in c and "党员" in c:
                out["political"] = "partyOrLeague"
            elif "党员" in c:
                out["political"] = "party"
            else:
                notes.append(c)  # 只限团员之类,系统未建模
            continue
        m = _YEARS.search(c)
        if m:
            years = cn_to_int(m.group(1))
            if years is None:
                warnings.append(f"未识别的基层工作年限:{c!r}")
            else:
                out["grassroots"] = years
            continue
        m = _AGE_RELAX.search(c)
        if m:
            rr["ageRelaxedTo"] = int(m.group(1))
            continue
        m = _AGE_MAX.search(c)
        if m and "年龄" in c:
            out["ageMax"] = int(m.group(1) or m.group(2))
            continue
        if re.search(r"户籍|生源", c) and not re.search(r"面向|退役", c):
            residency.append(c)
            continue
        if re.search(r"面向.*(?:村|社区).*(?:书记|主任)|优秀村", c):
            identity.append(c)
            continue
        if re.search(r"残疾", c):
            identity.append(c)
            continue
        if re.search(r"面向服务基层项目人员", c):
            continue  # 由职位代码分组处理
        if re.search(r"退役", c):
            identity.append(c)
            continue
        if _ENGLISH.search(c):
            notes.append(c)
            continue
        if "法律职业资格" in c:
            if c.startswith("法律类专业"):
                notes.append(c)  # 只对法律类专业报考者有此要求,是否适用于你需人工判断
            else:
                rr["legalQualification"] = True
            continue
        if _STAGE.search(c):
            ug_stage.append(c)
            continue
        if re.search(r"工作经历|工作经验", c):
            work.append(c)
            continue
        if re.search(r"(?:取得|具有|持有|具备).{0,30}(?:证书|资格|证)", c):
            certificates.append(c)
            continue
        if _INFO.search(c):
            continue
        if _HARD.search(c):
            notes.append(c)

    if notes:
        rr["notes"] = notes
    if residency:
        rr["residency"] = residency
    if certificates:
        rr["certificates"] = certificates
    if work:
        rr["workExperience"] = work
    if ug_stage:
        rr["ugStage"] = ug_stage
    if identity:
        rr["identity"] = identity
    out["rr"] = rr
    return out


def group_of(code: str, groups: list[dict[str, Any]]) -> dict[str, Any] | None:
    n = cn_to_int(code)
    if n is None:
        return None
    for g in groups:
        lo, hi = g["range"]
        if lo <= n <= hi:
            return g
    return None


# ---------------- 主入口 ----------------


def build_position(exam_id: str, cfg: dict[str, Any], raw: dict[str, Any], majors: MajorTable) -> Position:
    warnings: list[str] = []
    area_code = text(raw.get("地区代码"))
    unit_code = text(raw.get("单位代码"))
    code = text(raw.get("职位代码"))
    dept_code = f"{area_code}{unit_code}"
    org = text(raw.get("单位名称"))
    other_text = text(raw.get("其它"))
    level_key = text(raw.get("隶属关系"))
    if level_key not in _ORG_LEVEL:
        warnings.append(f"未识别的隶属关系:{level_key!r}")

    edu = normalize_edu(text(raw.get("学历")), warnings)
    parsed = parse_other(other_text, warnings)
    rr: dict[str, Any] = dict(parsed["rr"])

    group = group_of(code, cfg.get("codeGroups") or [])
    projects: list[str] = []
    attr = "普通职位"
    if group:
        attr = group["label"]
        if group.get("freshAlt"):
            rr["freshAlt"] = group["freshAlt"]
            rr["freshOnly"] = True
            rr.setdefault("gradYear", cfg["graduateYear"])
        if group.get("projects"):
            projects = list(group["projects"])
        if group.get("identity"):
            rr.setdefault("identity", []).append(group["identity"])
        if group.get("residency"):
            rr.setdefault("residency", []).append(group["residency"])
        if group.get("note"):
            rr.setdefault("notes", []).append(group["note"])

    is_police = bool(_POLICE_HINT.search(org) or "视力" in other_text)
    if is_police:
        rr["ageSpecial"] = True  # 公安/司法警察年龄按专门通知执行,公告级年龄线只能作参考

    major_text = text(raw.get("专业"))
    major_id = majors.register(major_text)
    if majors.rules[major_id]["warnings"]:
        warnings.extend(majors.rules[major_id]["warnings"])

    rule = cfg["ageRule"]
    pos: Position = {
        "id": f"{exam_id}:{dept_code}:{code}",
        "code": code,
        "deptCode": dept_code,
        "org": org,
        "unit": "",
        "orgType": "",
        "orgLevel": _ORG_LEVEL.get(level_key, level_key),
        "title": text(raw.get("职位名称")),
        "examCategory": f"{text(raw.get('考试类别'))}类",
        "attr": attr,
        "dist": "",
        "intro": text(raw.get("职位简介")),
        "headcount": to_int(raw.get("招考人数"), warnings, "招考人数"),
        "location": text(raw.get("地区名称")),
        "hukou": "",
        "edu": edu,
        "eduText": text(raw.get("学历")),
        "degree": parsed["degree"],
        "political": parsed["political"],
        "grassroots": parsed["grassroots"],
        "projects": projects,
        "majorId": major_id,
        "remark": other_text,
        "rr": sparse(rr),
        "interviewRatio": "",
        "skillTest": "",
        "site": "",
        "phones": [],
        "sheet": text(raw.get("_sheet")),
    }
    age_cap = parsed.get("ageMax")
    relaxed = rr.get("ageRelaxedTo")
    if relaxed is not None and relaxed < rule["maxAge"]:
        # 「年龄可放宽至35周岁」:基础年龄线更严(如公安、监狱职位),放宽后的上限就是绝对上限,
        # 比公告级 38 周岁更严,所以直接作为该职位的年龄上限;是否能享受放宽仍需核对,由 ageSpecial 提示
        age_cap = min(age_cap, relaxed) if age_cap else relaxed
        pos["rr"].pop("ageRelaxedTo", None)
        pos["rr"]["ageSpecial"] = True
    if age_cap:
        # 备注写明的更严年龄线(如「年龄不超过35周岁」)
        pos["ageMax"] = min(age_cap, rule["maxAge"])
        pos["ageMaxFresh"] = pos["ageMax"]
    extras = []
    ratio = text(raw.get("开考比例"))
    if ratio:
        extras.append(["开考比例", f"{ratio}:1"])
    if extras:
        pos["extras"] = extras
    if warnings:
        pos["warnings"] = warnings
    return pos

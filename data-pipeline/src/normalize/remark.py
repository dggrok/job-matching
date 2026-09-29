"""备注(自由文本)规则抽取。

只抽取"明确、常见、可以放心判定"的硬条件;其余内容原样保留,由前端展示备注原文。
抽不出来的条件不会被默认为"符合"——前端会提示用户查看备注原文。

输出字段:
{
  "freshOnly": bool,                # 限应届
  "gradYear": int | None,           # 限 N 届毕业生里的 N
  "gender": "male" | "female" | None,
  "maxAge": int | None,             # 备注里写明的更严年龄上限(周岁)
  "ageRelaxedTo": int | None,       # "年龄放宽到 N 周岁"(需满足特定条件,待确认)
  "cet": {"UG": 4, "PG": 6} | {"ANY": 4} | None,   # 大学英语等级要求
  "cetAltAllowed": bool,            # 雅思/托福/英语专业等级可替代
  "residency": [str],               # 户籍/生源地限制原句
  "certificates": [str],            # 职业资格/执业证书要求原句
  "legalQualification": bool,       # 需要法律职业资格证书
  "workExperience": [str],          # 工作经历要求原句
  "minServiceYears": int | None,    # 最低服务年限(信息性)
  "majorAnyLevel": bool,            # 各学历阶段对应专业之一即可
  "needAllStageDegrees": bool,      # 研究生须同时具有本科和研究生学历学位
}
"""

from __future__ import annotations

import re
from typing import Any

_SPLIT = re.compile(r"[\n；;。]")
_NUMBERING = re.compile(r"^\s*\d+\s*[\.、．]\s*")

_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def split_sentences(text: str) -> list[str]:
    out = []
    for piece in _SPLIT.split(text or ""):
        piece = _NUMBERING.sub("", piece).strip(" ,，、")
        if piece:
            out.append(piece)
    return out


def _to_int(s: str) -> int | None:
    if s.isdigit():
        return int(s)
    return _CN_NUM.get(s)


def extract_remark(text: str) -> dict[str, Any]:
    sents = split_sentences(text)
    joined = "\uff1b".join(sents)
    out: dict[str, Any] = {
        "freshOnly": False,
        "gradYear": None,
        "gender": None,
        "maxAge": None,
        "ageRelaxedTo": None,
        "cet": None,
        "cetAltAllowed": False,
        "residency": [],
        "certificates": [],
        "legalQualification": False,
        "workExperience": [],
        "minServiceYears": None,
        "majorAnyLevel": False,
        "needAllStageDegrees": False,
    }

    # ---- 应届 / 届别 ----
    m = re.search(r"(\d{4})届", joined)
    if m:
        out["freshOnly"] = True
        out["gradYear"] = int(m.group(1))
    elif re.search(r"(?<!非)应届", joined):
        out["freshOnly"] = True

    # ---- 性别 ----
    male = bool(re.search(r"限男|仅限男|男性", joined))
    female = bool(re.search(r"限女|仅限女|女性", joined))
    if male != female:
        out["gender"] = "male" if male else "female"

    # ---- 年龄 ----
    relax = re.search(r"年龄放宽到\s*(\d{2})\s*周岁", joined)
    if relax:
        out["ageRelaxedTo"] = int(relax.group(1))
    else:
        age = re.search(
            r"(?:年龄(?:条件)?(?:为|在)?|报考年龄(?:条件)?(?:为|不超过)?)\s*(\d{2})\s*周岁(?:以下|及以下)?",
            joined,
        )
        if age:
            out["maxAge"] = int(age.group(1))

    # ---- 英语 ----
    for s in sents:
        # 必须明确是"大学英语/CET"的等级要求,避免把 "英语专业四级" 之类的替代证书当成要求
        if not re.search(r"大学英语|英语[四六]级|CET", s, re.I):
            continue
        if "四级" in s and "六级" in s and "本科" in s and "研究生" in s:
            out["cet"] = {"UG": 4, "PG": 6}
        elif "六级" in s:
            out["cet"] = out["cet"] or {"ANY": 6}
        elif "四级" in s:
            out["cet"] = out["cet"] or {"ANY": 4}
    if out["cet"] is not None and re.search(r"雅思|托福|英语专业[四八]级", joined):
        out["cetAltAllowed"] = True

    # ---- 户籍 / 生源 ----
    for s in sents:
        if re.search(r"户籍|户口|生源", s) and not re.search(r"集体户口|落户", s):
            out["residency"].append(s)

    # ---- 资格证书 ----
    for s in sents:
        if re.search(r"毕业证|学位证", s):
            continue
        if re.search(r"英语|四级|六级|CET", s):
            continue
        if re.search(r"(?:取得|持有|具有|具备).{0,30}(?:证书|资格|证)", s):
            out["certificates"].append(s)
    out["legalQualification"] = "法律职业资格" in joined

    # ---- 工作经历 ----
    for s in sents:
        if re.search(r"工作经历|工作经验", s):
            out["workExperience"].append(s)

    # ---- 最低服务年限(信息性) ----
    m = re.search(r"最低服务(?:年限|期)(?:为)?\s*([一二三四五六七八九十\d]+)\s*年", joined)
    if m:
        out["minServiceYears"] = _to_int(m.group(1))

    # ---- 专业相关的说明 ----
    if re.search(r"各学历阶段对应专业之一", joined):
        out["majorAnyLevel"] = True
    if re.search(r"同时具有本科和研究生|各阶段均需取得相应学历和学位|本科和研究生学历学位", joined):
        out["needAllStageDegrees"] = True

    return out

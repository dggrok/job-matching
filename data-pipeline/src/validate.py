"""构建期自动校验:数据不对就让构建失败,而不是悄悄产出错误数据。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .normalize.position import MajorTable, Position

# 专业条目解析失败(整段无法切分)的职位占比超过该阈值则构建失败
MAJOR_FAIL_RATIO = 0.01


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(
    positions: list[Position],
    majors: MajorTable,
    cfg: dict[str, Any],
    sheet_counts: dict[str, int],
) -> Report:
    rep = Report()
    total = len(positions)
    headcount = sum(p["headcount"] for p in positions)

    # 1) 唯一键:国考的职位代码在全表并不唯一,唯一键是 部门代码 + 职位代码
    ids = Counter(p["id"] for p in positions)
    dup = [k for k, v in ids.items() if v > 1]
    if dup:
        rep.errors.append(f"存在重复的职位唯一键(部门代码+职位代码)共 {len(dup)} 个,例如 {dup[:3]}")

    # 2) 与官方公告披露的总数比对
    official = cfg.get("official") or {}
    if official.get("positions") is not None and official["positions"] != total:
        rep.errors.append(f"职位总数 {total} 与官方公布的 {official['positions']} 不一致")
    if official.get("headcount") is not None and official["headcount"] != headcount:
        rep.errors.append(f"招考人数合计 {headcount} 与官方公布的 {official['headcount']} 不一致")

    # 3) 枚举字段出现未识别值 → 说明格式变了,必须人工处理
    enum_warn = [
        (p["id"], w)
        for p in positions
        for w in p.get("warnings", [])
        if w.startswith(("未识别", "招考人数不是数字", "服务基层项目含未识别"))
    ]
    if enum_warn:
        sample = "; ".join(f"{i}: {w}" for i, w in enum_warn[:3])
        rep.errors.append(f"有 {len(enum_warn)} 处枚举字段无法识别,例如 {sample}")

    # 4) 专业整段解析失败的比例
    major_fail = sum(1 for p in positions if "专业无法切分出有效条目" in p.get("warnings", []))
    if total and major_fail / total > MAJOR_FAIL_RATIO:
        rep.errors.append(f"专业无法解析的职位占比 {major_fail / total:.2%},超过阈值 {MAJOR_FAIL_RATIO:.0%}")

    # ---- 统计信息(不影响是否通过,写入报告供人工核对)----
    unresolved_pos = 0
    unresolved_names: Counter[str] = Counter()
    for p in positions:
        rule = majors.rules[p["majorId"]]
        has_unres = False
        for seg in rule["segments"]:
            for t in seg["tokens"]:
                if not t["resolved"]:
                    has_unres = True
                    unresolved_names[f"{t.get('likelyLevel')}:{t['name'] or t['raw']}"] += 1
        unresolved_pos += has_unres

    rep.stats = {
        "positions": total,
        "headcount": headcount,
        "sheets": sheet_counts,
        "distinctMajorTexts": len(majors.rules),
        "majorUnlimited": sum(1 for p in positions if majors.rules[p["majorId"]]["unlimited"]),
        "positionsWithUnresolvedMajor": unresolved_pos,
        "topUnresolvedMajorNames": unresolved_names.most_common(30),
        "police": sum(1 for p in positions if p.get("police")),
        "freshOnly": sum(1 for p in positions if p["rr"].get("freshOnly")),
        "genderLimited": sum(1 for p in positions if p["rr"].get("gender")),
        "cetRequired": sum(1 for p in positions if p["rr"].get("cet")),
        "residencyLimited": sum(1 for p in positions if p["rr"].get("residency")),
    }
    return rep

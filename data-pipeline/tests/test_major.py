"""专业解析:表驱动测试,样本均取自 2026 年度国考职位表的真实写法。"""

import pytest


def tokens(rule, level=None):
    return [
        t
        for s in rule["segments"]
        if level is None or s["level"] == level
        for t in s["tokens"]
    ]


def test_unlimited(parser):
    for text in ("专业不限", "不限专业", "不限"):
        rule = parser.parse(text)
        assert rule["unlimited"] is True
        assert rule["segments"] == []


def test_class_by_name(parser):
    rule = parser.parse("电子信息类、计算机类")
    ts = tokens(rule)
    assert [t["refs"] for t in ts] == [["UG:0807"], ["UG:0809"]]
    assert all(t["resolved"] and not t["partial"] for t in ts)


def test_major_by_name_ug_only_when_tagged(parser):
    rule = parser.parse("本科：电子信息工程、通信工程")
    ts = tokens(rule, "UG")
    assert [t["refs"] for t in ts] == [["UG:080701"], ["UG:080703"]]


def test_code_plus_name(parser):
    rule = parser.parse("本科：120203K会计学、120204财务管理；研究生：120201会计学、1253会计")
    ug = tokens(rule, "UG")
    pg = tokens(rule, "PG")
    assert [t["refs"] for t in ug] == [["UG:120203K"], ["UG:120204"]]
    # 120201 是研究生二级学科(工商管理下的会计学):归到一级学科 1202,标为待确认
    assert pg[0]["refs"] == ["PG:1202"] and pg[0]["partial"] is True
    assert pg[1]["refs"] == ["PG:1253"] and not pg[1]["partial"]


def test_segments_with_variant_markers(parser):
    text = "以本科专业报考：法学类；以研究生专业报考：0301法学、0351法律"
    rule = parser.parse(text)
    assert [s["level"] for s in rule["segments"]] == ["UG", "PG"]
    assert tokens(rule, "UG")[0]["refs"] == ["UG:0301"]
    assert [t["refs"] for t in tokens(rule, "PG")] == [["PG:0301"], ["PG:0351"]]


def test_big_college_marker(parser):
    rule = parser.parse("大学本科：0401教育学类（教育学、教育技术学）、1305设计学类； 研究生：0401教育学、0451教育")
    ug = tokens(rule, "UG")
    assert ug[0]["refs"] == ["UG:0401"]
    # 括号里列举的子专业属于限定,匹配时应降级为待确认
    assert ug[0]["qualifiers"] and ug[0]["qualifiers"][0]["kind"] == "restrict"


def test_exclusion_qualifier_is_resolved(parser):
    rule = parser.parse("法学类（不含知识产权、监狱学、司法警察学专业）")
    t = tokens(rule)[0]
    q = t["qualifiers"][0]
    assert q["kind"] == "exclude"
    assert "UG:030102T" in q["refs"]  # 知识产权
    assert "UG:030103T" in q["refs"]  # 监狱学


def test_code_in_parentheses(parser):
    rule = parser.parse("计算机科学与技术（0812）、软件工程（0835）")
    ts = tokens(rule)
    assert ts[0]["codes"] == ["0812"]
    assert "PG:0812" in ts[0]["refs"]


def test_name_followed_by_code(parser):
    rule = parser.parse("计算机类0809、统计学类0712")
    ts = tokens(rule)
    assert ts[0]["refs"] == ["UG:0809"]
    assert ts[1]["refs"] == ["UG:0712"]


def test_category_suffix(parser):
    rule = parser.parse("工学门类、法学门类")
    ts = tokens(rule)
    # 必须命中门类本身,而不是同名的本科专业"法学"
    assert ts[0]["refs"] == ["UG:08", "PG:08"]
    assert ts[1]["refs"] == ["UG:03", "PG:03"]


def test_alias_is_partial(parser):
    rule = parser.parse("财会审计类")
    t = tokens(rule)[0]
    assert t["resolved"] and t["partial"]
    assert "UG:120203K" in t["refs"]


def test_class_suffix_fallback_is_partial(parser):
    rule = parser.parse("软件工程类")
    t = tokens(rule)[0]
    assert t["resolved"] and t["partial"]


def test_unresolved_second_level_discipline(parser):
    rule = parser.parse("民商法学、诉讼法学")
    ts = tokens(rule)
    assert not any(t["resolved"] for t in ts)
    assert all(t["likelyLevel"] == "PG" for t in ts)


def test_unresolved_class_like_name_is_ug(parser):
    rule = parser.parse("经济金融类")
    t = tokens(rule)[0]
    assert not t["resolved"] and t["likelyLevel"] == "UG"


def test_secondary_code_maps_to_first_level_as_partial(parser):
    rule = parser.parse("030105民商法、030103宪法学与行政法学")
    ts = tokens(rule)
    assert ts[0]["refs"] == ["PG:0301"] and ts[0]["partial"] is True
    assert ts[1]["refs"] == ["PG:0301"] and ts[1]["partial"] is True


def test_empty_text(parser):
    rule = parser.parse("")
    assert rule["warnings"] == ["专业为空"]


@pytest.mark.parametrize("text", ["本科或研究生专业为会计（学）、财务管理、审计（学）"])
def test_any_level_marker_and_xue_suffix(parser, text):
    rule = parser.parse(text)
    assert rule["segments"][0]["level"] == "ANY"
    ts = tokens(rule)
    # 会计(学) → 会计学
    assert "UG:120203K" in ts[0]["refs"]

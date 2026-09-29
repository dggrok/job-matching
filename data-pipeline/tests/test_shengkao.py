"""省考(浙江、江苏)标准化测试:样本均取自 2026 年度职位表的真实写法。"""

from pathlib import Path

import pytest

from src.catalog.jiangsu_ref import load_ref, parse_ref_text
from src.normalize.jiangsu import JiangsuMajorTable, parse_other
from src.normalize.major import MajorParser
from src.normalize.zhejiang import infer_region, normalize_major_text, parse_age, parse_identity

ROOT = Path(__file__).resolve().parent.parent


# ---------------- 浙江 ----------------


def test_zj_identity_simple():
    w: list[str] = []
    assert parse_identity("不限", w) == {}
    assert parse_identity("2026年应届毕业生", w) == {"freshOnly": True, "gradYear": 2026}
    assert parse_identity("2年以上基层工作经历", w) == {"grassroots": 2}
    assert parse_identity("优秀村干部", w) == {"identity": ["限优秀村干部"]}
    assert w == []


def test_zj_identity_projects_and_alt():
    w: list[str] = []
    out = parse_identity(
        "服务基层项目人员或在军队服役满5年的高校毕业生退役军人或符合条件的具有本科以上学历安排工作的退役军士和义务兵或符合条件的乡镇事业编制人员",
        w,
    )
    assert out["projects"] == ["west", "shanhai", "sanzhi", "veteran", "soldier"]
    assert "乡镇事业编制人员" in out["altIdentity"]
    assert w == []


def test_zj_identity_unknown_warns():
    w: list[str] = []
    assert parse_identity("持有某某证书人员", w) == {}
    assert w and "未识别" in w[0]


def test_zj_age():
    w: list[str] = []
    assert parse_age("年龄要求18至38周岁", w) == {"ageMin": 18, "ageMax": 38, "ageMaxFresh": 38}
    assert parse_age("年龄要求18至38周岁（2026年硕士以上应届毕业生放宽至43周岁）", w) == {
        "ageMin": 18,
        "ageMax": 38,
        "ageMaxFresh": 43,
    }
    assert parse_age("年龄要求18至30周岁", w)["ageMax"] == 30
    village = parse_age("年龄要求现任村“两委”正职18至43周岁（非现任村“两委”正职18至38周岁且具有国家承认的大专以上学历）", w)
    assert village["ageMax"] == 38 and village["ageRelaxedTo"] == 43
    assert w == []
    assert parse_age("看不懂的写法", w) == {}
    assert w


@pytest.mark.parametrize(
    "org,expected",
    [
        ("浙江省社会保险和就业服务中心", "省级"),
        ("杭州市富阳区乡镇机关", "杭州市"),
        ("淳安县乡镇机关", "杭州市"),
        ("瑞安市人民法院", "温州市"),
        ("宁波市鄞州区人民检察院", "宁波市"),
    ],
)
def test_zj_infer_region(org, expected):
    assert infer_region(org) == expected


def test_zj_normalize_major_text():
    assert normalize_major_text("研究生所学专业要求为：法学类；本科所学专业要求为：法学类") == "研究生：法学类；本科：法学类"


def test_zj_pg_class_suffix_exact(index):
    text = "研究生：理论经济学类"
    strict = MajorParser(index).parse(text)["segments"][0]["tokens"][0]
    exact = MajorParser(index, pg_class_suffix_exact=True).parse(text)["segments"][0]["tokens"][0]
    assert strict["partial"] is True  # 国考口径:「类」后缀属于推断,降级为待确认
    assert exact["partial"] is False and exact["refs"] == ["PG:0201"]  # 浙江口径:即一级学科,精确命中


# ---------------- 江苏 ----------------


def test_js_other_basic():
    w: list[str] = []
    out = parse_other("取得相应学位，面向2026年普通高校应届毕业生，中共党员（含预备），女性", w)
    assert out["degree"] == "matchHighest"
    assert out["political"] == "party"
    assert out["rr"]["freshOnly"] is True and out["rr"]["gradYear"] == 2026
    assert out["rr"]["gender"] == "female"
    assert w == []


def test_js_other_grassroots_legal_english():
    w: list[str] = []
    out = parse_other("取得相应学位，具有两年以上基层工作经历，取得国家法律职业资格证书（A类），取得大学英语六级考试证书，男性", w)
    assert out["grassroots"] == 2
    assert out["rr"]["legalQualification"] is True
    assert out["rr"]["gender"] == "male"
    assert out["rr"]["notes"] == ["取得大学英语六级考试证书"]


def test_js_other_ug_stage_and_ignorable():
    w: list[str] = []
    out = parse_other("取得相应学位，本科阶段为法律类专业并取得相应学位，单侧矫正视力低于5.0不合格", w)
    assert out["rr"]["ugStage"] == ["本科阶段为法律类专业并取得相应学位"]
    assert "notes" not in out["rr"]  # 视力属于可忽略的体检条款
    assert w == []


def test_js_ref_parse_real_file():
    ref = load_ref(ROOT / "catalogs" / "source" / "jiangsu-2026-major-ref.txt")
    assert len(ref) >= 45
    assert {"PG", "UG"} <= set(ref["法律类"])
    assert "法学" in ref["法律类"]["UG"] or any("法学" in x for x in ref["法律类"]["UG"])


def test_js_ref_parse_minimal():
    lines = ["专业大类"]
    for i in range(1, 32):
        lines += [str(i), f"测试{i}类", "法学理论，民商法学", "法学，知识产权", "法律事务"]
    ref = parse_ref_text("\n".join(lines))
    assert len(ref) == 31
    assert ref["测试1类"]["PG"] == ["法学理论", "民商法学"]
    assert ref["测试1类"]["UG"] == ["法学", "知识产权"]


def test_js_ref_parse_rejects_bad_text():
    with pytest.raises(ValueError):
        parse_ref_text("这不是专业参考目录")


def test_js_major_table_cat_resolves(parser, index):
    ref = load_ref(ROOT / "catalogs" / "source" / "jiangsu-2026-major-ref.txt")
    table = JiangsuMajorTable(parser, ref, index)
    mid = table.register("法律类")
    tok = table.rules[mid]["segments"][0]["tokens"][0]
    assert tok["cat"] == "法律类" and tok["resolved"] is True
    refs = table.cat_refs["法律类"]
    assert "UG:030101K" in refs  # 本科法学专业
    assert "PG:0301" in refs  # 法学 → 研究生一级学科法学

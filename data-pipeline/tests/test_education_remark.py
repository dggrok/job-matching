from src.normalize.education import (
    normalize_degree,
    normalize_education,
    normalize_grassroots_years,
    normalize_political,
    normalize_projects,
)
from src.normalize.remark import extract_remark


def test_education_enum():
    w: list[str] = []
    assert normalize_education("本科及以上", w) == ["本科", "硕士", "博士"]
    assert normalize_education("仅限本科", w) == ["本科"]
    assert normalize_education("本科或硕士研究生", w) == ["本科", "硕士"]
    assert normalize_education("硕士研究生及以上", w) == ["硕士", "博士"]
    assert w == []
    assert normalize_education("研究生", w) == []
    assert w and "未识别" in w[0]


def test_other_enums():
    w: list[str] = []
    assert normalize_degree("与最高学历相对应的学位", w) == "matchHighest"
    assert normalize_political("中共党员或共青团员", w) == "partyOrLeague"
    assert normalize_grassroots_years("二年", w) == 2
    assert normalize_grassroots_years("五年以上", w) == 5
    assert w == []


def test_projects():
    w: list[str] = []
    assert normalize_projects("无限制", w) == []
    got = normalize_projects("大学生村官、“三支一扶”计划、大学生志愿服务西部计划", w)
    assert got == ["village", "sanzhi", "west"]
    assert w == []
    assert normalize_projects("某个新项目", w) == []
    assert w and "未识别" in w[0]


def test_remark_fresh_and_year():
    r = extract_remark("2026届高校毕业生，男性，在本单位最低服务年限为5年")
    assert r["freshOnly"] and r["gradYear"] == 2026
    assert r["gender"] == "male"
    assert r["minServiceYears"] == 5

    r = extract_remark("1.限应届高校毕业生报考，请在备注栏中注明本人具有应届高校毕业生身份")
    assert r["freshOnly"] and r["gradYear"] is None


def test_remark_non_fresh_is_not_fresh_only():
    r = extract_remark("非应届高校毕业生报考，应具有2年以上商业性金融机构、经济部门或相关专业工作经历")
    assert not r["freshOnly"]
    assert r["workExperience"]


def test_remark_gender():
    assert extract_remark("工作强度大、任务重，限男性")["gender"] == "male"
    assert extract_remark("仅限男性报考")["gender"] == "male"
    assert extract_remark("限女性")["gender"] == "female"
    assert extract_remark("咨询电话:0451-86429698")["gender"] is None


def test_remark_age():
    r = extract_remark("要求服务期满、考核合格，报考年龄不超过30周岁")
    assert r["maxAge"] == 30
    r = extract_remark("年龄在30周岁以下")
    assert r["maxAge"] == 30
    r = extract_remark("持有一等船长适任证书，年龄放宽到43周岁以下，报考前请与招考部门联系")
    assert r["ageRelaxedTo"] == 43 and r["maxAge"] is None


def test_remark_cet():
    r = extract_remark("本科生大学英语四级考试425分及以上，研究生大学英语六级考试425分及以上")
    assert r["cet"] == {"UG": 4, "PG": 6}
    r = extract_remark("大学英语六级成绩在425分及以上（雅思成绩在6分及以上、托福成绩在80分及以上）")
    assert r["cet"] == {"ANY": 6} and r["cetAltAllowed"]
    r = extract_remark("大学英语四级成绩在425分及以上")
    assert r["cet"] == {"ANY": 4} and not r["cetAltAllowed"]
    # 只提到"英语专业四级"的不是等级要求
    assert extract_remark("取得英语专业四级或专业八级合格证书亦可")["cet"] is None


def test_remark_residency_ignores_collective_hukou():
    assert extract_remark("可为符合条件人员办理集体户口")["residency"] == []
    assert extract_remark("限内蒙古户籍或生源")["residency"] == ["限内蒙古户籍或生源"]


def test_remark_certificates_and_legal():
    r = extract_remark("取得法律职业资格证书（A类）")
    assert r["legalQualification"] and r["certificates"]
    r = extract_remark("具有相应学历的毕业证书和学位证书")
    assert r["certificates"] == []


def test_remark_major_flags():
    r = extract_remark("职位要求专业为职位要求最低学历及以上各学历阶段对应专业之一即可")
    assert r["majorAnyLevel"]
    r = extract_remark("研究生学历报考者须同时具有本科和研究生学历学位")
    assert r["needAllStageDegrees"]

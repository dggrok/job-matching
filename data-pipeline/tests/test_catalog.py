from collections import Counter


def test_catalog_counts(catalogs):
    ug = Counter(n["kind"] for n in catalogs["UG"])
    pg = Counter(n["kind"] for n in catalogs["PG"])
    # 2025 本科目录:12 个门类、93 个专业类、840 个专业(与目录文本正则计数一致)
    assert ug == {"category": 12, "class": 93, "major": 840}
    # 2022 研究生目录:14 个门类、181 个一级学科与专业学位类别
    assert pg == {"category": 14, "discipline": 181}


def test_electronic_information_engineering(index):
    node = index.get("UG:080701")
    assert node["name"] == "电子信息工程"
    assert node["note"] == "可授工学或理学学士学位"
    assert index.chain("UG:080701") == ["UG:080701", "UG:0807", "UG:08"]
    assert index.by_code("UG", "080701")["id"] == "UG:080701"


def test_code_suffix_is_ignored(index):
    # 国考写 120203K,目录里也是 120203K;去掉后缀也应该能查到
    assert index.by_code("UG", "120203K")["name"] == "会计学"
    assert index.by_code("UG", "120203")["name"] == "会计学"


def test_namespaces_do_not_collide(index):
    # 本科专业类 0301(法学类)与研究生一级学科 0301(法学)都是 4 位,必须分命名空间
    assert index.get("UG:0301")["name"] == "法学类"
    assert index.get("PG:0301")["name"] == "法学"


def test_name_lookup_prefers_specific_kind(index):
    # "法学" 在本科既是专业(030101K)又是门类名的一部分;只应返回最具体的专业
    hits = index.find_by_name("UG", "法学")
    assert [n["id"] for n in hits] == ["UG:030101K"]
    # 研究生 "法学" 是一级学科 0301,而不是门类 03
    hits = index.find_by_name("PG", "法学")
    assert [n["id"] for n in hits] == ["PG:0301"]


def test_professional_degree_flag(index):
    assert index.get("PG:0854")["professional"] is True
    assert index.get("PG:0812")["professional"] is False

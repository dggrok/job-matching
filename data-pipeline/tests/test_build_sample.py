"""集成测试:用 2026 年度样表跑完整管线。样表不在时跳过(raw/ 不入库)。"""

from pathlib import Path

import pytest
import yaml

from src.importers.guokao import GuokaoImporter
from src.normalize.position import MajorTable, build_position
from src.validate import validate

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "raw" / "guokao-2026.xls"

pytestmark = pytest.mark.skipif(not SAMPLE.exists(), reason="缺少 raw/guokao-2026.xls 样表")


@pytest.fixture(scope="module")
def built(parser):
    exams = yaml.safe_load((ROOT / "config" / "exams.yaml").read_text(encoding="utf-8"))
    cfg = exams["guokao-2026"]
    rows = GuokaoImporter().load(SAMPLE)
    majors = MajorTable(parser)
    positions = [build_position("guokao-2026", cfg, r, majors) for r in rows]
    return cfg, rows, majors, positions


def test_totals_match_official(built):
    cfg, rows, majors, positions = built
    assert len(positions) == cfg["official"]["positions"] == 20714
    assert sum(p["headcount"] for p in positions) == cfg["official"]["headcount"] == 38119


def test_unique_key_is_dept_plus_code(built):
    _, _, _, positions = built
    assert len({p["id"] for p in positions}) == len(positions)
    # 单独的职位代码并不唯一,这是踩过的坑,用测试固化下来
    assert len({p["code"] for p in positions}) < len(positions)


def test_validation_passes(built):
    cfg, rows, majors, positions = built
    rep = validate(positions, majors, cfg, {})
    assert rep.errors == []


def test_no_unknown_enums(built):
    _, _, _, positions = built
    bad = [p["id"] for p in positions if any(w.startswith("未识别") for w in p.get("warnings", []))]
    assert bad == []


def test_police_flag_only_for_city_level_and_below(built):
    _, _, _, positions = built
    for p in positions:
        if p.get("police"):
            assert p["attr"] == "公安机关人民警察职位"
            assert p["orgLevel"] in ("市（地）级", "县（区）级及以下")

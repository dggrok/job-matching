"""一键构建:读取原始职位表 → 标准化 → 校验 → 输出前端数据。

用法(在 data-pipeline/ 目录下):
    .venv/bin/python -m src.build --exam guokao-2026
    .venv/bin/python -m src.build --all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .catalog.index import CatalogIndex
from .catalog.parse import load_catalogs
from .importers.base import ImportError_
from .importers.guokao import GuokaoImporter
from .normalize.major import MajorParser
from .normalize.position import MajorTable, build_position
from .validate import validate

ROOT = Path(__file__).resolve().parent.parent  # data-pipeline/
DEFAULT_OUT = ROOT.parent / "web" / "public" / "data"

IMPORTERS = {"guokao": GuokaoImporter}


def dump(obj: Any, path: Path) -> str:
    """紧凑 JSON 写文件,返回内容 sha256 前 12 位。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    # default=str:YAML 里的日期(如 2025-10-14)会被解析成 date 对象,统一转成字符串
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_catalog_json(catalogs: dict[str, list[dict]], out: Path) -> None:
    """输出精简的目录数据:[id, 名称, 类型, 父级, 备注]。"""
    slim = {
        level: [[n["id"], n["name"], n["kind"], n["parent"], n.get("note")] for n in nodes]
        for level, nodes in catalogs.items()
    }
    slim["meta"] = {
        "UG": "《普通高等学校本科专业目录(2025年)》",
        "PG": "《研究生教育学科专业目录(2022年)》",
    }
    dump(slim, out / "catalog.json")


def build_exam(exam_id: str, cfg: dict[str, Any], index: CatalogIndex, out: Path) -> dict[str, Any]:
    importer = IMPORTERS[cfg["type"]]()
    raw_rows = importer.load(ROOT / cfg["file"])
    sheet_counts = dict(Counter(r["_sheet"] for r in raw_rows))

    majors = MajorTable(MajorParser(index))
    positions = [build_position(exam_id, cfg, r, majors) for r in raw_rows]

    report = validate(positions, majors, cfg, sheet_counts)
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / f"{exam_id}.json").write_text(
        json.dumps({"errors": report.errors, "stats": report.stats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[{exam_id}] 职位 {report.stats['positions']} 个, 招考 {report.stats['headcount']} 人")
    print(f"[{exam_id}] 各 Sheet: {report.stats['sheets']}")
    print(
        f"[{exam_id}] 专业含目录外名称的职位 {report.stats['positionsWithUnresolvedMajor']} 个 "
        f"(详见 reports/{exam_id}.json)"
    )
    if not report.ok:
        for e in report.errors:
            print(f"[{exam_id}] 校验失败: {e}", file=sys.stderr)
        raise SystemExit(1)

    data = {"examId": exam_id, "majorRules": majors.rules, "positions": positions}
    version = dump(data, out / exam_id / "positions.json")
    print(f"[{exam_id}] 校验通过, 数据版本 {version}")

    return {
        "id": exam_id,
        "name": cfg["name"],
        "type": cfg["type"],
        "year": cfg["year"],
        "graduateYear": cfg["graduateYear"],
        "publishedAt": cfg.get("publishedAt"),
        "signup": cfg.get("signup"),
        "writtenExam": cfg.get("writtenExam"),
        "source": cfg["source"],
        "sample": bool(cfg.get("sample")),
        "pending": False,
        "positions": report.stats["positions"],
        "headcount": report.stats["headcount"],
        "ageRule": cfg["ageRule"],
        "dataVersion": version,
        "file": f"{exam_id}/positions.json",
    }


def pending_entry(exam_id: str, cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": exam_id,
        "name": cfg["name"],
        "type": cfg["type"],
        "year": cfg["year"],
        "graduateYear": cfg["graduateYear"],
        "source": cfg["source"],
        "pending": True,
        "file": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="构建前端数据")
    ap.add_argument("--exam", action="append", help="考试 id,可重复,如 guokao-2026")
    ap.add_argument("--all", action="store_true", help="构建 exams.yaml 中所有非 pending 考试")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="输出目录")
    args = ap.parse_args()

    exams: dict[str, Any] = load_yaml(ROOT / "config" / "exams.yaml")
    targets = list(exams) if args.all else (args.exam or [])
    if not targets:
        ap.error("请指定 --exam <id> 或 --all")

    aliases = load_yaml(ROOT / "config" / "majors-alias.yaml")
    catalogs = load_catalogs(ROOT / "catalogs" / "source")
    index = CatalogIndex(catalogs, aliases)

    out: Path = args.out
    build_catalog_json(catalogs, out)

    manifest_path = out / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"exams": []}
    )
    by_id = {e["id"]: e for e in manifest["exams"]}

    try:
        for exam_id in targets:
            if exam_id not in exams:
                raise SystemExit(f"exams.yaml 中没有 {exam_id}")
            cfg = exams[exam_id]
            if cfg.get("pending") and not (ROOT / cfg["file"]).exists():
                print(f"[{exam_id}] 尚未发布(pending),跳过构建")
                by_id[exam_id] = pending_entry(exam_id, cfg)
                continue
            by_id[exam_id] = build_exam(exam_id, cfg, index, out)
    except ImportError_ as e:
        raise SystemExit(f"导入失败: {e}")

    manifest["exams"] = sorted(by_id.values(), key=lambda e: e["id"], reverse=True)
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dump(manifest, manifest_path)
    print(f"已写入 {out}")


if __name__ == "__main__":
    main()

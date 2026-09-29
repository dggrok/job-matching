"""浙江省考职位表导入器。

官方《浙江省各级机关单位公务员招考计划一览表》(xlsx)的结构(以 2026 年度为准,已实测):
- 3 个 Sheet:综合管理类、行政执法类、专业技术类;
- 每个 Sheet 第 1 行就是表头(没有免责说明行),之后是数据;
- 20 列,以列名而不是列序号取值。
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseImporter, ImportError_, RawRow, read_sheets

REQUIRED = (
    "招录单位名称",
    "职位代码",
    "职位名称",
    "职位属性",
    "职位大类",
    "招录人数",
    "学历要求",
    "学位要求",
    "现有身份要求",
    "政治面貌要求",
    "民族要求",
    "年龄要求",
    "专业要求",
    "备注",
)


class ZhejiangImporter(BaseImporter):
    required_columns = REQUIRED

    def load(self, path: Path) -> list[RawRow]:
        if not path.exists():
            raise ImportError_(f"找不到职位表文件: {path}")
        rows: list[RawRow] = []
        for sheet_name, data in read_sheets(path):
            header_idx = next(
                (i for i, line in enumerate(data[:5]) if "职位代码" in [str(c).strip() for c in line]),
                None,
            )
            if header_idx is None:
                raise ImportError_(f"Sheet「{sheet_name}」中找不到包含「职位代码」的表头行")
            header = [str(c).strip() for c in data[header_idx]]
            self.check_columns(header, f"Sheet「{sheet_name}」")
            for line in data[header_idx + 1 :]:
                row = dict(zip(header, line))
                if not str(row.get("职位代码", "")).strip():
                    continue
                row["_sheet"] = sheet_name
                rows.append(row)
        if not rows:
            raise ImportError_("未读取到任何职位")
        return rows

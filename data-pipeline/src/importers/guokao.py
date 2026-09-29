"""国考职位表导入器。

官方《招考简章》xls 的结构(以 2026 年度为准,已实测):
- 4 个 Sheet:中央党群机关、中央国家行政机关(本级)、省级以下直属机构、参照公务员法管理事业单位;
- 每个 Sheet 第 1 行是免责说明,第 2 行是表头,之后是数据;
- 27 列,以列名而不是列序号取值,这样列顺序变化不会出错。
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseImporter, ImportError_, RawRow, read_sheets

# 缺任何一列就无法正确解析,直接报错
REQUIRED = (
    "部门代码",
    "部门名称",
    "招考职位",
    "职位属性",
    "职位代码",
    "机构层级",
    "考试类别",
    "招考人数",
    "专业",
    "学历",
    "学位",
    "政治面貌",
    "基层工作最低年限",
    "服务基层项目工作经历",
    "工作地点",
    "备注",
)


class GuokaoImporter(BaseImporter):
    required_columns = REQUIRED

    def load(self, path: Path) -> list[RawRow]:
        if not path.exists():
            raise ImportError_(f"找不到职位表文件: {path}")
        rows: list[RawRow] = []
        for sheet_name, data in read_sheets(path):
            header_idx = self._find_header(data)
            if header_idx is None:
                raise ImportError_(f"Sheet「{sheet_name}」中找不到包含「职位代码」的表头行")
            header = [str(c).strip() for c in data[header_idx]]
            self.check_columns(header, f"Sheet「{sheet_name}」")
            for line in data[header_idx + 1 :]:
                row = dict(zip(header, line))
                code = str(row.get("职位代码", "")).strip()
                if not code:
                    continue  # 空行或合计行
                row["_sheet"] = sheet_name
                rows.append(row)
        if not rows:
            raise ImportError_("未读取到任何职位")
        return rows

    @staticmethod
    def _find_header(data: list[list]) -> int | None:
        for i, line in enumerate(data[:10]):
            cells = [str(c).strip() for c in line]
            if "职位代码" in cells and "部门名称" in cells:
                return i
        return None

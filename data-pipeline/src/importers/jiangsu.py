"""江苏省考职位表导入器。

官方公告附件是一个压缩包,解压后是 16 份 xls(省级机关、13 个设区市、地方统计系统、监狱戒毒系统)。
把它们全部放进同一个目录(如 raw/jiangsu-2026/),本导入器读取目录下所有 xls/xlsx。

每份文件一个 Sheet:第 1 行是标题,第 2 行空行,第 3 行是表头,之后是数据;
表头文字里夹有全角空格(如「学　历」「隶属  关系」),读取时统一去掉。
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import BaseImporter, ImportError_, RawRow, read_sheets

REQUIRED = (
    "隶属关系",
    "地区代码",
    "地区名称",
    "单位代码",
    "单位名称",
    "职位代码",
    "职位名称",
    "考试类别",
    "招考人数",
    "学历",
    "专业",
    "其它",
)

_SPACES = re.compile(r"[\s\u3000]+")


class JiangsuImporter(BaseImporter):
    required_columns = REQUIRED

    def load(self, path: Path) -> list[RawRow]:
        if not path.exists():
            raise ImportError_(f"找不到职位表目录: {path}")
        files = sorted(p for p in path.iterdir() if p.suffix.lower() in (".xls", ".xlsx") and not p.name.startswith("~"))
        if not files:
            raise ImportError_(f"目录 {path} 下没有 xls/xlsx 文件,请把官方压缩包解压到这里")
        rows: list[RawRow] = []
        for f in files:
            for sheet_name, data in read_sheets(f):
                header_idx = next(
                    (i for i, line in enumerate(data[:8]) if "职位代码" in [_SPACES.sub("", str(c)) for c in line]),
                    None,
                )
                if header_idx is None:
                    raise ImportError_(f"{f.name} 的 Sheet「{sheet_name}」中找不到包含「职位代码」的表头行")
                header = [_SPACES.sub("", str(c)) for c in data[header_idx]]
                self.check_columns(header, f"{f.name}")
                for line in data[header_idx + 1 :]:
                    row = dict(zip(header, line))
                    if not str(row.get("职位代码", "")).strip():
                        continue
                    row["_sheet"] = sheet_name
                    row["_file"] = f.name
                    rows.append(row)
        if not rows:
            raise ImportError_("未读取到任何职位")
        return rows

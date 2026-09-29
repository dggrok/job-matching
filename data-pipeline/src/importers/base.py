"""导入器基类与通用工具。

每个数据源(国考、浙江、江苏……)写一个 importer,只负责把原始文件读成
"列名 → 原始值" 的字典列表(RawRow),标准化由 normalize 层统一完成。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

RawRow = dict[str, Any]


class ImportError_(Exception):
    """导入失败(表头缺列、文件损坏等),直接终止构建。"""


class BaseImporter(ABC):
    #: 必须存在的列名;缺任何一列都会报错并列出缺失列
    required_columns: tuple[str, ...] = ()

    @abstractmethod
    def load(self, path: Path) -> list[RawRow]:
        """读取文件,返回原始行。每行包含 `_sheet`(所在 Sheet 名)。"""

    def check_columns(self, header: list[str], where: str) -> None:
        missing = [c for c in self.required_columns if c not in header]
        if missing:
            raise ImportError_(f"{where} 缺少必需列: {', '.join(missing)}")


def read_sheets(path: Path) -> list[tuple[str, list[list[Any]]]]:
    """读取 xls/xlsx 的所有 Sheet,返回 [(sheet 名, 行列表)]。"""
    suffix = path.suffix.lower()
    if suffix == ".xls":
        import xlrd

        wb = xlrd.open_workbook(str(path))
        return [
            (s.name, [s.row_values(r) for r in range(s.nrows)]) for s in wb.sheets()
        ]
    if suffix == ".xlsx":
        import openpyxl

        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        out = []
        for ws in wb.worksheets:
            out.append(
                (
                    ws.title,
                    [["" if v is None else v for v in row] for row in ws.iter_rows(values_only=True)],
                )
            )
        return out
    raise ImportError_(f"不支持的文件类型: {path.name}")

"""Выгрузка списков админки в Excel (.xlsx)."""

from __future__ import annotations

import re
from io import BytesIO
from typing import TYPE_CHECKING, Any

from markupsafe import Markup
from openpyxl import Workbook
from openpyxl.styles import Font
from starlette.responses import StreamingResponse

if TYPE_CHECKING:
    from sqladmin.models import ModelView


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Markup):
        text = str(value)
        if "fa-check" in text:
            return "Да"
        if "fa-times" in text:
            return "Нет"
        return re.sub(r"<[^>]+>", "", text).strip()
    return str(value)


def _safe_filename(stem: str) -> str:
    cleaned = re.sub(r"[^\w\s\-]", "", stem, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned or "export"


async def build_xlsx_response(
    model_view: ModelView,
    rows: list[Any],
    filename_stem: str,
) -> StreamingResponse:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Данные"

    prop_names = model_view._export_prop_names
    headers = [model_view._column_labels.get(name, name) for name in prop_names]
    worksheet.append(headers)
    for cell in worksheet[1]:
        cell.font = Font(bold=True)

    for row in rows:
        values = []
        for name in prop_names:
            _, formatted = await model_view.get_list_value(row, name)
            values.append(_cell_text(formatted))
        worksheet.append(values)

    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            if cell.value is not None:
                max_length = max(max_length, len(str(cell.value)))
        worksheet.column_dimensions[column_letter].width = min(max_length + 2, 60)

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    filename = f"{_safe_filename(filename_stem)}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename={filename}"},
    )

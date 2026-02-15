from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from excel_handler.excel_io import export_result_to_excel, read_excel, validate_file_extension
from utils.data_cleaning import standardize_dataframe
from utils.field_mapping import REQUIRED_KEYS, infer_field_mapping, validate_manual_mapping
from utils.reconciliation import reconcile_orders

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

SESSION_CACHE: dict[str, dict] = {}


async def _save_upload(file: UploadFile) -> Path:
    if not file.filename or not validate_file_extension(file.filename):
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file.filename}")
    file_id = uuid4().hex
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)
    return file_path


@router.post("/api/upload")
async def upload_files(official_file: UploadFile = File(...), service_file: UploadFile = File(...)):
    official_path = await _save_upload(official_file)
    service_path = await _save_upload(service_file)

    official_df = read_excel(official_path)
    service_df = read_excel(service_path)

    official_mapping = infer_field_mapping(official_df.columns.tolist())
    service_mapping = infer_field_mapping(service_df.columns.tolist())

    session_id = uuid4().hex
    SESSION_CACHE[session_id] = {
        "official_path": str(official_path),
        "service_path": str(service_path),
        "official_columns": official_df.columns.tolist(),
        "service_columns": service_df.columns.tolist(),
        "official_auto_mapping": official_mapping.mapping,
        "service_auto_mapping": service_mapping.mapping,
    }

    return JSONResponse(
        {
            "session_id": session_id,
            "official_columns": official_df.columns.tolist(),
            "service_columns": service_df.columns.tolist(),
            "official_auto_mapping": official_mapping.mapping,
            "service_auto_mapping": service_mapping.mapping,
            "official_missing": official_mapping.missing_keys,
            "service_missing": service_mapping.missing_keys,
            "required_keys": REQUIRED_KEYS,
        }
    )


@router.post("/api/compare")
async def compare_orders(
    session_id: str = Form(...),
    official_mapping: str = Form(...),
    service_mapping: str = Form(...),
):
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="会话不存在，请重新上传文件")

    session = SESSION_CACHE[session_id]
    official_map = validate_manual_mapping(json.loads(official_mapping), session["official_columns"])
    service_map = validate_manual_mapping(json.loads(service_mapping), session["service_columns"])

    if official_map.missing_keys or service_map.missing_keys:
        raise HTTPException(
            status_code=400,
            detail={
                "official_missing": official_map.missing_keys,
                "service_missing": service_map.missing_keys,
            },
        )

    official_df = read_excel(Path(session["official_path"]))
    service_df = read_excel(Path(session["service_path"]))

    official_cleaned, official_warnings = standardize_dataframe(official_df, official_map.mapping, "官方订单")
    service_cleaned, service_warnings = standardize_dataframe(service_df, service_map.mapping, "客服统计")

    result_df, summary, compare_warnings = reconcile_orders(official_cleaned, service_cleaned)

    session["result_df"] = result_df.to_dict(orient="records")
    session["summary"] = summary

    return JSONResponse(
        {
            "warnings": official_warnings + service_warnings + compare_warnings,
            "summary": summary,
            "rows": session["result_df"],
        }
    )


@router.get("/api/export/{session_id}")
async def export_excel(session_id: str):
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="会话不存在")

    session = SESSION_CACHE[session_id]
    result_rows = session.get("result_df")
    summary = session.get("summary")
    if not result_rows or not summary:
        raise HTTPException(status_code=400, detail="请先执行比对")

    import pandas as pd

    result_df = pd.DataFrame(result_rows)
    excel_bytes = export_result_to_excel(result_df, summary)
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reconciliation_{session_id}.xlsx"},
    )

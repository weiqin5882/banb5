from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd



def reconcile_orders(official_df: pd.DataFrame, service_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float], List[str]]:
    warnings: List[str] = []

    official = official_df.copy()
    service = service_df.copy()

    official["in_official"] = True
    service["in_service"] = True

    merged = official.merge(
        service[["order_id", "product_name", "sales_amount", "cost_amount", "order_status", "in_service"]],
        on="order_id",
        how="outer",
        suffixes=("_official", "_service"),
    )

    def status_label(row: pd.Series) -> str:
        if row.get("in_official") and row.get("in_service"):
            return "正常匹配"
        if row.get("in_official") and not row.get("in_service"):
            return "客服漏记"
        if row.get("in_service") and not row.get("in_official"):
            return "客服多记"
        return "未知"

    merged["status_flag"] = merged.apply(status_label, axis=1)

    merged["product_name"] = merged["product_name_official"].combine_first(merged["product_name_service"])
    merged["sales_amount"] = merged["sales_amount_official"].combine_first(merged["sales_amount_service"]).fillna(0.0)
    merged["cost_amount"] = merged["cost_amount_official"].combine_first(merged["cost_amount_service"]).fillna(0.0)
    merged["order_status"] = merged["order_status_official"].combine_first(merged["order_status_service"])

    merged["profit"] = merged["sales_amount"] - merged["cost_amount"]
    merged["is_loss"] = merged["profit"] < 0
    merged["final_status"] = merged.apply(
        lambda r: f"{r['status_flag']}|亏损订单" if r["is_loss"] else r["status_flag"],
        axis=1,
    )

    result = merged[["order_id", "product_name", "sales_amount", "cost_amount", "profit", "final_status", "is_loss", "status_flag"]].copy()
    result = result.reset_index(drop=True)
    result.insert(0, "index", result.index + 1)

    summary = {
        "total_sales": float(result["sales_amount"].sum()),
        "total_cost": float(result["cost_amount"].sum()),
        "total_profit": float(result["profit"].sum()),
        "order_count": int(result["order_id"].nunique()),
        "matched_count": int((result["status_flag"] == "正常匹配").sum()),
        "missing_count": int((result["status_flag"] == "客服漏记").sum()),
        "extra_count": int((result["status_flag"] == "客服多记").sum()),
        "loss_count": int(result["is_loss"].sum()),
    }

    if result.empty:
        warnings.append("比对结果为空，请检查上传数据与状态过滤条件")

    return result, summary, warnings

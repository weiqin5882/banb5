from __future__ import annotations

import re
from typing import Dict, List, Tuple

import pandas as pd

VALID_STATUSES = {"交易成功", "已发货"}



def clean_order_id(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", "", text)
    digits = re.sub(r"\D", "", text)
    return digits



def clean_money(value: object) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).replace("¥", "").replace(",", "").strip()
    text = re.sub(r"\s+", "", text)
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0



def standardize_dataframe(df: pd.DataFrame, mapping: Dict[str, str], source: str) -> Tuple[pd.DataFrame, List[str]]:
    warnings: List[str] = []
    renamed = df.rename(columns={
        mapping["order_id"]: "order_id",
        mapping["product_name"]: "product_name",
        mapping["order_status"]: "order_status",
        mapping["sales_amount"]: "sales_amount",
        mapping["cost_amount"]: "cost_amount",
    }).copy()

    cols = ["order_id", "product_name", "order_status", "sales_amount", "cost_amount"]
    standardized = renamed[cols].copy()

    standardized["order_id_raw"] = standardized["order_id"]
    standardized["order_id"] = standardized["order_id"].apply(clean_order_id)
    non_numeric_mask = standardized["order_id"].eq("")
    if non_numeric_mask.any():
        warnings.append(f"{source}: 检测到 {non_numeric_mask.sum()} 条非数字或空订单号，已标记异常")

    standardized["sales_amount"] = standardized["sales_amount"].apply(clean_money)
    standardized["cost_amount"] = standardized["cost_amount"].apply(clean_money)

    standardized["order_status"] = standardized["order_status"].fillna("").astype(str).str.strip()
    before_filter = len(standardized)
    standardized = standardized[standardized["order_status"].isin(VALID_STATUSES)]
    filtered_count = before_filter - len(standardized)
    if filtered_count:
        warnings.append(f"{source}: 已过滤 {filtered_count} 条无效状态订单")

    duplicate_count = standardized.duplicated(subset=["order_id"], keep=False).sum()
    if duplicate_count:
        warnings.append(f"{source}: 检测到 {duplicate_count} 条重复订单号，保留最后一条记录")
        standardized = standardized.drop_duplicates(subset=["order_id"], keep="last")

    standardized["is_invalid_order_id"] = standardized["order_id"].eq("")
    return standardized, warnings

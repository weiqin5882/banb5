from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

REQUIRED_KEYS = ["order_id", "product_name", "order_status", "sales_amount", "cost_amount"]

FIELD_ALIASES: Dict[str, List[str]] = {
    "order_id": ["订单编号", "订单号", "子订单号", "单号", "order id", "order_no"],
    "product_name": ["商品名称", "产品", "商品", "product", "item name"],
    "order_status": ["订单状态", "状态", "status", "交易状态"],
    "sales_amount": ["实付金额", "销售金额", "金额", "应收", "paid", "sales"],
    "cost_amount": ["成本价", "进货价", "成本", "cost", "purchase"],
}


@dataclass
class MappingResult:
    mapping: Dict[str, Optional[str]]
    missing_keys: List[str]



def normalize_header(header: str) -> str:
    return "".join(str(header).strip().lower().split())



def infer_field_mapping(columns: List[str]) -> MappingResult:
    normalized_columns = {normalize_header(c): c for c in columns}
    mapping: Dict[str, Optional[str]] = {k: None for k in REQUIRED_KEYS}

    for key, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_header(alias)
            if normalized_alias in normalized_columns:
                mapping[key] = normalized_columns[normalized_alias]
                break
        if mapping[key] is None:
            for col in columns:
                ncol = normalize_header(col)
                if any(normalize_header(alias) in ncol for alias in aliases):
                    mapping[key] = col
                    break

    missing = [k for k, v in mapping.items() if v is None]
    return MappingResult(mapping=mapping, missing_keys=missing)



def validate_manual_mapping(mapping: Dict[str, str], columns: List[str]) -> MappingResult:
    normalized_cols = set(columns)
    normalized_mapping: Dict[str, Optional[str]] = {}
    for key in REQUIRED_KEYS:
        selected = mapping.get(key)
        normalized_mapping[key] = selected if selected in normalized_cols else None

    missing = [k for k, v in normalized_mapping.items() if v is None]
    return MappingResult(mapping=normalized_mapping, missing_keys=missing)

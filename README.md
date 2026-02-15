# 订单比对与利润核算系统

基于 FastAPI + Pandas 的网页版财务对账工具，用于自动比对官方订单与客服统计订单，识别漏单/错单并完成利润核算。

## 功能

- 双文件上传：官方订单表、客服统计表（支持 `.xlsx/.xls/.et`）
- 自动字段识别 + 手动映射兜底
- 数据清洗：订单号、金额、状态过滤、重复订单处理
- 三向比对：正常匹配 / 客服漏记 / 客服多记
- 利润核算：单笔利润、总销售额、总成本、总利润
- 亏损订单前端高亮 + 导出 Excel 标红
- 一键导出标准对账报表

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

浏览器访问：`http://127.0.0.1:8000`

## 项目结构

```text
main.py                 # 入口
api/routes.py           # 接口层
utils/field_mapping.py  # 字段智能识别与校验
utils/data_cleaning.py  # 清洗规则
utils/reconciliation.py # 比对与利润核算
excel_handler/excel_io.py # Excel读写与导出样式
templates/index.html    # 页面模板
static/js/app.js        # 前端交互逻辑
static/css/style.css    # 样式
```

## 核心业务规则

- 有效状态：`交易成功`、`已发货`
- 单笔利润 = 销售金额 - 成本金额
- 比对主键：订单号（清洗后纯数字）
- 标记规则：
  - 官方有 + 客服有 → 正常匹配
  - 官方有 + 客服无 → 客服漏记
  - 客服有 + 官方无 → 客服多记
  - 单笔利润 < 0 → 叠加 `亏损订单`

## 注意事项

- `.et` 文件读取依赖运行环境对对应格式解析能力；若失败请先转为 `.xlsx`。
- 单文件建议 10 万行以内，使用 Pandas 向量化处理。

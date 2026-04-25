# 项目记忆

更新时间：2026-04-23

## 项目定位

这是一个基于 Flask 的个人内部管理系统，当前主业务是包材库存管理，同时扩展了微信小店 Excel 数据导入导出和 VPS 简易监控。

项目入口是 `app.py`，运行端口是 `5001`：

```bash
python3 app.py
```

依赖安装：

```bash
pip install -r requirements.txt
```

## 技术栈

- 后端：Flask 3.x
- 数据库：SQLite
- Excel 处理：pandas、openpyxl
- 前端：Jinja2 模板 + 原生 HTML/CSS/JavaScript

## 核心文件结构

- `app.py`：Flask 应用入口，注册所有蓝图。
- `templates/`：页面模板。
- `inventory/routes.py`：库存盘点页面、盘点快照写入、消耗分析接口。
- `purchase/routes.py`：采购记录页面、采购文本解析、新增包材、提交采购记录。
- `stocking/routes.py`：入库操作页面、待入库列表、已入库列表、入库提交、补打标签记录。
- `logs/routes.py`：操作日志查看、登录保护、回滚操作。
- `wechat_shop/`：微信小店订单、资金流水、售后 Excel 导入导出。
- `vps_monitor/`：VPS 状态和 xray 日志查看。
- `common/excel_utils.py`：Excel 文件名和表头规范化工具。
- `db/`：旧的数据库连接/初始化代码，目前与主应用使用的库路径不一致，需要谨慎看待。

## 蓝图和 URL

`app.py` 当前注册：

- `/`：总入口页面。
- `/inventory`：库存盘点。
- `/purchase`：采购入库。
- `/stockin`：操作入库。
- `/logs`：操作日志。
- `/wechat_shop`：微信小店。
- `/vps-monitor`、`/vps-status`、`/vps-log`：VPS 监控相关页面/接口。

## 数据库现状

主应用统一配置：

```python
app.config['DATABASE_PATH'] = 'data/main.db'
```

已确认当前工作区存在：

- `data/main.db`：主应用正在使用的数据库，包材业务和微信小店数据都在这里。
- `data/packaging.db`：空文件，来自旧 `db/dbconnection.py` 的路径，目前主应用不使用。
- `data/wechat_shop.db`：旧/独立微信小店库文件，目前主应用配置不会使用它。

`data/main.db` 中实际存在的主要表包括：

- `pack_item`：包材型号。
- `purchase_record`：采购记录。
- `stock_in_record`：入库记录。
- `pack_stock_snapshot`：库存盘点快照。
- `operation_logs`：操作日志和回滚依据。
- `wechat_orders`：微信小店订单。
- `wechat_fund_flow`：微信小店资金流水。
- `wechat_after_sales`：微信小店售后。
- `wechat_shop_data_status`：微信小店数据状态概览。

`db/dbconnection.py` 使用的是 `data/packaging.db`，而主应用使用 `data/main.db`。这部分像是旧代码或未接入代码，修改数据库相关逻辑时要先确认真实目标库。

当前记录数快照：

- `pack_item`：19 条。
- `purchase_record`：107 条。
- `stock_in_record`：128 条。
- `pack_stock_snapshot`：1445 条。
- `operation_logs`：79 条。
- `wechat_orders`：252 条。
- `wechat_fund_flow`：620 条。
- `wechat_after_sales`：21 条。
- `wechat_shop_data_status`：3 条。

实际 schema 里的关键约束：

- `pack_item.name` 是唯一值。
- `purchase_record.order_id` 是唯一值。
- `pack_stock_snapshot` 有唯一索引 `ux_pack_stock_snapshot_ts_spec`，约束 `(stocktake_ts, spec)`。
- `stock_in_record.purchase_id` 逻辑关联 `purchase_record.purchase_id`，但 schema 没有声明外键。
- `operation_logs` 有 `ip_address` 字段，是后续追加进来的列。

当前 `pack_item` 型号包括：`10`、`10.5`、`11`、`11.5`、`12.5`、`5`、`6`、`6.5`、`7`、`7.5`、`8`、`8.5`、`9`、`9.5`、`中泡`、`大泡`、`小泡`、`缠绕膜`、`气泡柱`。

## 包材业务流程

1. 在 `/purchase` 粘贴或填写采购数据。
2. 系统解析包材型号，必要时通过接口新增 `pack_item`。
3. 提交采购记录写入 `purchase_record`。
4. 在 `/stockin` 查看未完全入库的采购记录，并提交入库到 `stock_in_record`。
5. 在 `/inventory` 录入盘点快照到 `pack_stock_snapshot`。
6. 盘点分析根据起止盘点数量、区间入库袋数、最近一次入库每袋件数估算消耗件数。

## 操作日志和回滚

采购、入库、盘点等写操作会写入 `operation_logs`，字段里保存 `old_data` 和 `new_data`。

`/logs` 有简单密码保护：

- 密码硬编码在 `logs/routes.py`。
- Session key 和 Flask `secret_key` 也在代码里硬编码。

回滚逻辑根据 `table_name`、`record_id`、`action_type` 和 `old_data` 执行 INSERT/UPDATE/DELETE 的反向操作。这里使用动态 SQL，后续如果开放更多表，要特别注意表名和字段名白名单。

## 微信小店模块

微信小店模块在 `/wechat_shop/`。

主要能力：

- 导入订单 Excel。
- 导入资金流水 Excel。
- 导入售后 Excel。
- 查看每类数据的记录数和时间范围。
- 按时间、字段、筛选条件导出 Excel。

表字段映射集中在 `wechat_shop/table_schemas.py`，服务逻辑集中在 `wechat_shop/services.py`。

导入时会做：

- 文件类型检查。
- 表头归一化。
- 必填列校验。
- 建表/补字段。
- 按指定 key 去重。
- 更新 `wechat_shop_data_status`。

## 已知注意点

- `purchase/_init_.py` 文件名疑似拼错，正常包初始化一般是 `__init__.py`。当前导入直接用 `purchase.routes`，在现代 Python 命名空间包机制下仍可能可用，但后续最好统一。
- `db/dbinit_db.py` 里写的是 `from .connection import get_connection`，但当前文件是 `dbconnection.py`，这段可能已经不可运行。
- README 内容有重复段落，也有测试写入句子，后续可以整理。
- 目前没有自动化测试目录。
- 当前仓库虽然已有 `data/main.db`，但没有数据库初始化脚本覆盖主业务所有表。后续若要换电脑或重建库，这是优先补的基础设施。

## 后续开发建议

- 开始任何功能前，先读本文件、`app.py` 和对应模块的 `routes.py`。
- 涉及数据库前，优先以 `data/main.db` 的真实 schema 为准，不要只看 `db/` 旧代码。
- 新增写操作时，最好同步写 `operation_logs`，保持回滚能力一致。
- 微信小店字段变动优先改 `wechat_shop/table_schemas.py`，不要在导入逻辑里散写字段名。
- 长期建议补一个真正的 `schema.sql` 或初始化脚本，把 `data/main.db` 所需表一次性建出来。
## [2026-04-24 20:45] 修改记录
- 修改内容：引入多用户登录与模块授权体系（v1）
  - 新增 auth/ 模块（登录/登出/改密 + 管理员用户管理）
  - 新增 user、user_module_permission 两张表
  - 首次启动自动创建管理员 GeorgeJi/GeorgeJi123456（临时密码，部署后立即修改）
  - 废弃 /logs 的 chenxi98 硬编码密码，/logs/login、/logs/logout 路由直接删除
  - inventory/purchase/stockin/logs/wechat_shop 5 个模块加 @module_required
  - vps_monitor 模块（/vps-monitor、/vps-status、/vps-log）改为 @admin_required（管理员专属）
  - / 首页加 @login_required，按权限过滤卡片显示
  - operation_logs.operator 由硬编码 "system" 改为自动写入当前登录用户名
  - app.secret_key 改为读取环境变量 APP_SECRET_KEY，默认值用于开发
- 修改文件：
  - 新增：auth/__init__.py、auth/schema.py、auth/services.py、auth/decorators.py、auth/routes.py、auth/admin_routes.py
  - 新增：templates/login.html、templates/change_password.html、templates/admin_users.html、templates/admin_user_edit.html
  - 修改：app.py、templates/index.html、logs/routes.py、inventory/routes.py、purchase/routes.py、stocking/routes.py、wechat_shop/routes.py、vps_monitor/routes.py
- 修改原因：建立统一的多用户访问控制，淘汰分散硬编码密码，vps_monitor 因性质敏感改为管理员专属
- 影响范围：所有业务页面现需登录后访问；旧 /logs/login、/logs/logout 路由删除；历史 operation_logs 记录不清洗
- 是否涉及数据库：是（新增 user、user_module_permission 两张表）
- 是否需要回滚：否（一次性改造；如需回滚可还原文件，新增空表不影响业务）

## [2026-04-25 19:05] 修改记录
- 修改内容：发票模块 Day 1.5 - 数据表补丁 + PDF 解析 PoC 扩展
  - invoice 表加列：project_name（如缺）、pdf_remark、is_usable（默认 0）、period_start、period_end
  - expected_amount 表加列：period_start、period_end
  - PoC 验证：样本 PDF 可提取 项目名称 + 备注栏；is_usable 自动判定规则确定（项目含"服务"或"推广" AND 备注不含"代扣代缴"）
  - 数据库已备份至 data/main_backup_before_invoice_day1_5_20260425_185401.db
- 修改文件：
  - 数据库：data/main.db（仅 ALTER TABLE，未触业务代码）
  - 备份：新增 main_backup_before_invoice_day1_5_20260425_185401.db
- 修改原因：业务必须捕获 PDF 上的"项目名称"和"备注栏"原文用于发票可用性自动判定；账期需支持手工录入起止日期
- 影响范围：仅数据库 schema 加列；尚无业务代码引用新列，运行时无破坏
- 是否涉及数据库：是
- 是否需要回滚：否（如需直接还原备份库）

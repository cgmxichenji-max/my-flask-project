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

## [2026-04-25 19:47] 修改记录
- 修改内容：发票模块 Step 2 — 基础数据 CRUD + 模块授权接入 + 首页入口
  - 新建 invoicing 蓝图，加 12 条路由（首页 1 / 开票主体 4 / 客户 5 / 别名 2）
  - 新建 4 个模板：invoicing_index、invoicing_billing_entities、invoicing_customers、invoicing_customer_detail
  - auth/services.py 加 'invoicing' 模块键 + 中文标签「发票核对」
  - app.py 注册 invoicing_bp（url_prefix=/invoicing）
  - templates/index.html 在微信小店与 VPS 监控之间加「发票核对」卡片，受 can_module(user, 'invoicing') 控制
  - 客户列表 LEFT JOIN customer_alias 显示别名集合，前端 JS 关键字筛选
  - 删除按钮统一二次确认弹窗；customer 删除手动级联清理 customer_alias（外键未启用）
- 修改文件：
  - 新增：invoicing/__init__.py、invoicing/routes.py
  - 新增：templates/invoicing_index.html、templates/invoicing_billing_entities.html、templates/invoicing_customers.html、templates/invoicing_customer_detail.html
  - 修改：auth/services.py、app.py、templates/index.html
- 修改原因：发票核对模块需要可视化 CRUD 入口；必须接入授权体系避免普通用户越权；客户列表需通过别名快速回溯销售方
- 影响范围：新增独立模块；现有模块路由与逻辑不动；现有非管理员用户默认无访问权限，需管理员主动授权；GeorgeJi 自动可见
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert）

## [2026-04-25 20:24] 修改记录
- 修改内容：发票模块 Step 3 — 应开金额 Excel 导入与列表查看
  - invoicing/routes.py 新增 expected_amounts 列表页与 import_expected_amounts 导入路由
  - 使用 openpyxl 读取 .xlsx/.xlsm，不新增依赖
  - 导入支持 Excel 列：达人/客户/带货账号昵称、应开金额/带货费用、平台、期间、开票主体、店铺、备注、账期起止日期
  - 页面表单提供默认开票主体、平台、期间、账期起止日期；Excel 缺少对应列时用默认值补齐
  - 未识别客户自动创建 customer(short_name=达人)
  - invoicing_index.html 增加“应开金额”入口卡片
  - 新增模板 templates/invoicing_expected_amounts.html，展示导入表单、导入结果和已导入记录列表
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_index.html
  - 新增：templates/invoicing_expected_amounts.html
- 修改原因：发票核对模块需要先录入应开金额，作为后续发票核对视图的基准数据
- 影响范围：仅发票核对模块；未修改数据库结构；现有业务模块不受影响
- 是否涉及数据库：是（运行导入功能时会写入 customer、expected_amount；本次自动验收使用临时库，真实 data/main.db 未写入测试数据）
- 是否需要回滚：否（如出问题 git revert）

## [2026-04-26 21:48] 修改记录
- 修改内容：发票模块 Step 3 补齐 — 客户匹配三段法 + 导入防重
  - invoicing/routes.py 导入处理函数：客户查找扩展为 short_name → full_name → alias 三段匹配，全空才自动新建
  - invoicing/routes.py 导入处理函数：写入 expected_amount 前检查 (customer_id, entity_id, platform, period, amount) 完全相同，是则跳过
  - 结果页/返回信息新增"跳过 X 行"统计
- 修改文件：invoicing/routes.py
- 修改原因：与 Step 3 PLAN 一致，避免重复导入和孤立客户
- 影响范围：仅发票模块导入逻辑；不影响 Step 2 已落地的 CRUD
- 是否涉及数据库：否
- 是否需要回滚：否

## [2026-04-26 22:10] 修改记录
- 修改内容：发票模块 Day 4.0 — invoice.customer_id 由 NOT NULL 改为 nullable
  - 通过 SQLite "建新表 → INSERT SELECT → DROP → RENAME" 四步迁移（事务包裹）
  - 字段顺序、默认值、外键、UNIQUE 约束保持不变
  - 仅 customer_id 的 NOT NULL 约束被去除
  - 迁移前 invoice 行数为 0，迁移零风险
  - 已验证 customer_id 可写入 NULL 后回滚测试行
- 修改文件：data/main.db（仅表结构）；备份：data/main_backup_before_day4_0_20260426_221023.db
- 修改原因：Step 4 发票上传需支持"暂不匹配客户"状态，customer_id 必须可 NULL，后续在待匹配列表页补匹配
- 影响范围：仅 invoice 表；无业务代码引用（路由尚未做），运行时无破坏
- 是否涉及数据库：是
- 是否需要回滚：否（如需还原直接用备份库覆盖）

## [2026-04-26 22:29] 修改记录
- 修改内容：发票模块 Step 4.1 — PDF 单张上传 + 自动解析 + 人工复核 + 入库 / 丢弃
  - 新建 invoicing/pdf_parser.py：纯函数模块，提取 invoice_number / invoice_date / amount / seller_name / buyer_name / project_name / pdf_remark / qr_content；自动建议 is_usable
  - 关键词阻断扩展为 3 条："代扣代缴"、"未按规定扣缴"、"不得作为所得税前合法有效扣除凭证"
  - invoicing/routes.py 新增 9 条路由（list / upload GET+POST / review / confirm / discard / pdf serve / pending pdf serve / match / delete）
  - 客户匹配三段：short_name → full_name → alias，无命中保持 NULL（不自动建客户）
  - 主体匹配：buyer_name 包含 entity.name 即命中
  - 重号检查：invoice_number 已存在则复核页阻止入库
  - 丢弃 = 完全不入库不归档；入库 = INSERT + 移动 PDF 至 data/invoice_pdfs/<entity 或 _unmatched_>/<year>/<invoice_number>.pdf
  - 新建 3 模板：invoicing_invoices_upload / invoicing_invoices_review / invoicing_invoices；invoicing_index 加第 4 张卡片「发票管理」
  - requirements.txt 补 4 个 PDF 依赖：pdfplumber 0.11.9、PyMuPDF 1.27.2.2、opencv-python(-headless) 4.13.0、Pillow 12.2.0
- 修改文件：
  - 新增：invoicing/pdf_parser.py、templates/invoicing_invoices_upload.html、templates/invoicing_invoices_review.html、templates/invoicing_invoices.html
  - 修改：invoicing/routes.py、templates/invoicing_index.html、requirements.txt
- 修改原因：完成"应开 vs 已开"核对的"已开"侧基础数据采集
- 影响范围：仅发票模块；新增 data/invoice_pdfs/ 与 data/invoice_pdfs_pending/ 两个 PDF 文件目录
- 是否涉及数据库：否（schema 不变，仅 INSERT/UPDATE/DELETE invoice 表）
- 是否需要回滚：否（如出问题 git revert + 删 data/invoice_pdfs* 目录）
## [2026-04-26 22:42] 修改记录
- 修改内容：发票模块 Step 5 — 应开 vs 已开核对视图
  - invoicing/routes.py 新增路由 /invoicing/reconciliation
  - 核心 SQL：expected CTE + invoiced CTE + UNION 模拟 FULL OUTER JOIN，按 (customer_id, entity_id) 聚合
  - 应开按 period_start/end 与筛选范围重叠匹配；已开按 invoice_date 在筛选范围内
  - 已开仅统计 is_usable = 1
  - 顶部 banner 显示未匹配（customer_id 或 entity_id 为 NULL）发票合计与跳转链接
  - 主表保留"未知客户/未知主体"行，diff 计算不变
  - 新建 templates/invoicing_reconciliation.html：筛选条 + 总计卡 + 主表 + 进度条 + 前端关键字筛选
  - invoicing_index.html 加第 5 张卡片「应开 vs 已开核对」
  - 自动化测试通过：临时库构造 3 客户 × 主体 + 1 NULL + 1 is_usable=0；金额、差额、banner、is_usable 排除均符合预期
- 修改文件：
  - 新增：templates/invoicing_reconciliation.html
  - 修改：invoicing/routes.py、templates/invoicing_index.html
- 修改原因：完成核对模块"第一性问题"答卷
- 影响范围：仅发票模块；不改 schema、不改其他业务
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert）

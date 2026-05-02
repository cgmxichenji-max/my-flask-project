# 项目记忆

## [2026-05-02 13:21] 修改记录
- 修改内容：修正微信小店原始数据导出默认日期，改为按当前数据状态表中的最早/最晚日期自动填充，避免写死未来日期导致导出空白；新增 common/download_utils.py 统一下载响应，微信小店 Excel 导出与发票批量 ZIP 下载改用标准下载函数；移除微信小店导出调试 print。
- 修改文件：common/download_utils.py；wechat_shop/routes.py；wechat_shop/services.py；templates/wechat_shop.html；invoicing/routes.py；PROJECT_MEMORY.md；PROJECT_MEMORY_FILE_STORAGE.md
- 修改原因：微信小店导出页面默认日期为 2026-03-01 到 2026-03-20，而实际微信小店数据集中在 2024-11 至 2025-03，导致按默认条件导出只有表头无数据；下载响应也需要与发票批量下载统一管理。
- 影响范围：微信小店原始数据导出默认日期和 Excel 下载响应；发票批量下载 ZIP 响应；不影响 Excel/PDF 上传、导入写库和核对计算。
- 是否涉及数据库：否
- 是否需要回滚：是，回滚上述代码文件即可。

## [2026-05-02 12:28] 修改记录
- 修改内容：服务器 nginx 站点配置增加 client_max_body_size 200m，解除 Excel 上传被 nginx 以 413 Request Entity Too Large 拦截的问题；同步补充 SERVER_RUNBOOK.md 中的上传限制说明。
- 修改文件：服务器 /etc/nginx/sites-available/flaskapp；SERVER_RUNBOOK.md；PROJECT_MEMORY.md；PROJECT_MEMORY_FILE_STORAGE.md
- 修改原因：服务器端测试微信小店导入时，大文件上传在到达 Flask 前被 nginx 默认请求体大小限制拦截，前端收到 HTTP 413。
- 影响范围：通过 nginx 访问的所有请求允许最大 200MB 请求体；主要影响 Excel/PDF 上传，不改变导入业务逻辑。
- 是否涉及数据库：否
- 是否需要回滚：是，将服务器 /etc/nginx/sites-available/flaskapp 恢复为 /etc/nginx/sites-available/flaskapp.backup_before_upload_limit_20260502_042757 后执行 nginx -t && systemctl reload nginx；文档改动可 git revert。

## [2026-05-02 12:18] 修改记录
- 修改内容：修正微信小店 Excel 导入控件，由只能选择文件夹改为可选择一个或多个 .xlsx/.xls 文件；导入 fetch 请求增加 JSON 期望请求头与非 JSON 响应兜底提示；认证/授权装饰器对 AJAX/JSON 请求返回 JSON 401/403，避免登录页 HTML 被前端当作 JSON 解析。
- 修改文件：templates/wechat_shop.html；auth/decorators.py；PROJECT_MEMORY.md；PROJECT_MEMORY_FILE_STORAGE.md
- 修改原因：服务器端测试导入时发现页面只能选择文件夹，且接口返回 HTML 时前端报 Unexpected token '<'，需要改为单文件/多文件选择并提供明确错误提示。
- 影响范围：微信小店 Excel 导入页面；AJAX/JSON 请求的登录失效和无权限错误返回格式。普通页面访问的登录跳转行为保持不变。
- 是否涉及数据库：否
- 是否需要回滚：是，回滚上述代码文件即可。

## [2026-05-02 11:47] 修改记录
- 修改内容：新增统一 Excel 上传暂存前序模块，微信小店订单/资金流水/售后 Excel 导入与发票核对应开金额 Excel 导入统一改为先保存到服务器独立批次临时目录，再从本地暂存文件读取导入；导入成功或失败后立即清理当前批次目录，并在导入前清理超过 2 小时的孤儿批次目录。新增 PROJECT_MEMORY_FILE_STORAGE.md 作为本聊天上传/文件系统专项记录。
- 修改文件：common/upload_staging.py；wechat_shop/routes.py；wechat_shop/services.py；invoicing/routes.py；PROJECT_MEMORY.md；PROJECT_MEMORY_FILE_STORAGE.md
- 修改原因：服务器端作为唯一正式运行环境时，Excel 导入需要先完成可靠落盘，避免导入阶段依赖浏览器请求流和网络连接稳定性，同时防止临时文件长期占用服务器硬盘或影响下次导入。
- 影响范围：微信小店 Excel 导入、发票核对应开金额 Excel 导入；不影响发票 PDF 上传、核对计算、库存采购入库等模块。
- 是否涉及数据库：否
- 是否需要回滚：是，回滚代码文件并删除 data/upload_staging/ 目录即可。

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
## [2026-04-30 14:32] 修改记录
- 修改内容：修正发票批量下载命名规则中的“开票平台”判断，优先按购买方名称识别澳柯、慕莲蔓、香娜露儿、快手等平台关键字；当其与归属平台不一致时，在账单周期后追加“开票平台”标记。
- 修改文件：invoicing/routes.py；PROJECT_MEMORY.md
- 修改原因：现有命名逻辑仅按销售方字段判断，导致部分应标记“开票澳柯”等差异平台的发票文件名未正确体现开票平台。
- 影响范围：仅发票列表批量下载 ZIP 内 PDF 的命名规则；不改数据库 schema、PDF 原文件和其他页面展示。
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
## [2026-04-27 11:01] 修改记录
- 修改内容：发票模块应开金额导入与客户别名规则修正
  - 应开金额导入页取消独立展示/采集 shop_name（店铺）与 remark（备注），业务上统一把“平台”作为“店铺/平台”使用
  - Excel 表头识别中将“店铺 / 店铺名称”并入 platform 字段识别范围
  - 应开金额列表删除旧“店铺”“备注”两列，保留“店铺/平台”“期间”“起止日期”“金额”等核心字段
  - 导入结果新增未导入明细：缺字段跳过和重复跳过都会显示 Excel 行号、原因、达人/客户、金额、店铺/平台、期间、开票主体
  - customer_alias 表去掉 alias 全局 UNIQUE 约束，允许同一个别名挂到多个客户/昵称下
  - 新增代码层防重：同一客户下重复添加同一个别名时跳过，避免重复行
  - 客户/发票自动匹配遇到同一 alias 对应多个客户时不再自动选第一条，改为保持未匹配或跳过，避免误归属
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_expected_amounts.html、templates/invoicing_customer_detail.html
  - 数据库：data/main.db（customer_alias 表去除 alias UNIQUE 约束）
  - 备份：data/main_backup_before_alias_expected_fix_20260427_110056.db
- 修改原因：实际导入反馈显示店铺/备注字段不符合当前使用方式，且需要明确展示未导入行；客户别名业务应支持一个别名关联多个达人昵称
- 影响范围：仅发票模块基础数据与应开金额导入；历史 expected_amount.shop_name / remark 数据不清洗，后续页面不再展示
- 是否涉及数据库：是（customer_alias 约束迁移，不改业务数据）
- 是否需要回滚：否（如需回滚可还原备份库并 git revert 文件改动）
## [2026-04-27 11:20] 修改记录
- 修改内容：发票模块应开金额导入交互继续修正
  - 导入结果新增固定弹窗：如存在缺字段跳过或重复跳过，页面显示“本次导入有未进入系统的数据”，需用户手动关闭，不会一闪而过
  - 弹窗和页面结果区均展示未进入系统的 Excel 行号、原因、达人/客户、金额、店铺/平台、期间、归属
  - 应开金额导入表单将“默认店铺/平台”从文本框改为下拉框，选项来自已维护的 billing_entity 名称
  - 选择“默认归属（用于核对）”时自动同步“默认店铺/平台”为同名选项，减少手工输入
  - 应开金额横表删除“主体”列，保留客户、店铺/平台、期间、起止日期、金额、创建时间
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_expected_amounts.html、PROJECT_MEMORY.md
- 修改原因：导入测试需要明确知道哪些 Excel 行没有进入系统及原因；当前业务把主体名称作为店铺/平台默认选项，横表不需要展示主体字段
- 影响范围：仅发票模块应开金额导入与列表展示；不改 schema，不影响其他模块
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 11:22] 修改记录
- 修改内容：发票模块导入测试数据清理
  - 按用户确认，清空 expected_amount、customer_alias、customer 三张导入相关表
  - 同步清理 sqlite_sequence 中上述三张表的自增序号，便于重新导入测试时 ID 从头开始
  - 保留 billing_entity 表数据（澳柯、香娜露儿等默认归属/店铺平台来源）
  - invoice 表本次未清理业务数据（执行前后均为 0 行）
  - 清理后计数：expected_amount=0、customer_alias=0、customer=0、invoice=0、billing_entity=2
- 修改文件：
  - 数据库：data/main.db
  - 备份：data/main_backup_before_clear_import_data_20260427_112250.db
  - 记录：PROJECT_MEMORY.md
- 修改原因：用户需要重新导入测试应开金额，需清空此前导入产生的应开金额、客户和别名数据
- 影响范围：仅发票模块导入测试数据；主体配置保留；不影响登录、权限和其他业务模块
- 是否涉及数据库：是（删除本地测试/导入数据）
- 是否需要回滚：否（如需恢复可用备份库覆盖）
## [2026-04-27 11:33] 修改记录
- 修改内容：发票模块达人/团长昵称管理与批量别名
  - 复核数据表后确认：customer.short_name 作为达人/团长昵称唯一值保留，customer_alias 作为昵称与别名/归属的多对多映射使用
  - customer_alias 新增唯一索引 idx_customer_alias_customer_id_alias，约束同一昵称不能重复添加同一别名，但允许同一别名关联多个昵称
  - 客户管理页面文案改为“达人/团长昵称管理”，列表字段改为“达人/团长昵称 / 法人公司名 / 别名归属集合”
  - 保留顶部筛选框，筛选范围包含昵称、法人公司名、别名归属集合
  - 昵称列表新增 checkbox 和全选功能，可批量给选中的达人/团长昵称添加同一个别名/归属名
  - 批量设置后返回列表并显示新增数量、已存在/无效跳过数量
  - 达人/团长昵称详情页同步改文案，说明一个别名可挂多个昵称，遇到多昵称共用别名时不自动匹配
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_customers.html、templates/invoicing_customer_detail.html、PROJECT_MEMORY.md
  - 数据库：data/main.db（新增 customer_alias(customer_id, alias) 唯一索引）
  - 备份：data/main_backup_before_customer_alias_bulk_20260427_113147.db
- 修改原因：导入的名称实际是达人/团长昵称，多个昵称可能对应同一个人或公司，需要在列表页批量维护别名/归属
- 影响范围：仅发票模块达人/团长昵称管理；不改 expected_amount / invoice schema
- 是否涉及数据库：是（新增唯一索引，不删除业务数据）
- 是否需要回滚：否（如需回滚可还原备份库并 git revert 文件改动）
## [2026-04-27 11:55] 修改记录
- 修改内容：发票模块达人/团长昵称唯一性改为“昵称 + 平台”
  - customer 表新增 platform 字段，并将唯一约束从 short_name 单字段改为 UNIQUE(short_name, platform)
  - 迁移时按 expected_amount.platform 回填既有 customer.platform；当前 339 个昵称均回填为“香娜露儿”
  - 应开金额导入匹配/创建达人昵称时改为按 short_name + platform 查找，不同平台同名昵称会创建不同 customer 记录
  - 达人/团长昵称管理页改为按 short_name 聚合显示，一行展示该昵称在澳柯、香娜露儿、快手、幕莲蔓四个平台/店铺的佣金实时汇总
  - 横表删除法人/公司名、别名/归属集合、创建时间、操作列，仅保留勾选框、达人/团长昵称、四个平台/店铺佣金
  - 批量设置别名改为按昵称批量处理：选中一个昵称时，会给该昵称下所有平台记录同时添加别名
  - 后续“点击昵称显示其别名开票的各平台/店铺发票金额”暂未实现
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_customers.html、PROJECT_MEMORY.md
  - 数据库：data/main.db（customer 表重建并新增 platform 字段及 UNIQUE(short_name, platform)）
  - 备份：data/main_backup_before_customer_platform_unique_20260427_115249.db
- 修改原因：业务确认达人/团长昵称不是全局唯一，唯一维度应为昵称 + 平台/店铺；管理页需要按昵称聚合并展示各平台佣金
- 影响范围：发票模块应开金额导入、达人/团长昵称管理、别名批量维护；不改 invoice / expected_amount schema
- 是否涉及数据库：是（customer 表结构迁移）
- 是否需要回滚：否（如需恢复可用备份库覆盖并 git revert 文件改动）
## [2026-04-27 12:05] 修改记录
- 修改内容：发票模块达人/团长昵称管理新增别名视图与别名维护
  - 达人/团长昵称管理页新增“昵称列表 / 别名列表”切换
  - 昵称列表保留批量设置别名功能，并在最后一列显示该昵称已有别名，可单独删除某个昵称下的某个别名
  - 别名列表按 alias 聚合显示下属昵称，以及澳柯、香娜露儿、快手、幕莲蔓四个平台/店铺的佣金实时合计
  - 别名列表支持重命名 alias；如果新 alias 已存在于同一昵称下，则自动合并并删除重复旧 alias 记录
  - 别名列表支持删除 alias，会从所有昵称下移除该 alias
  - 为避免嵌套表单，批量设置别名的 checkbox 使用 HTML form 属性关联到批量表单，行内删除/改名使用独立表单
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_customers.html、PROJECT_MEMORY.md
- 修改原因：需要按别名查看其下属昵称及佣金合计，并允许修正输错的别名
- 影响范围：仅发票模块达人/团长昵称管理页面与 customer_alias 维护逻辑；不改 schema
- 是否涉及数据库：否（新增路由会在用户操作时更新 customer_alias）
- 是否需要回滚：否（如出问题 git revert 文件改动）
## [2026-04-27 12:11] 修改记录
- 修改内容：发票模块昵称/别名管理页新增总金额汇总
  - 昵称列表顶部新增“所有昵称”佣金汇总，按澳柯、香娜露儿、快手、幕莲蔓四个平台/店铺分别显示总金额
  - 别名列表顶部新增“所有别名”佣金汇总，按澳柯、香娜露儿、快手、幕莲蔓四个平台/店铺分别显示总金额
  - 汇总金额由 invoicing/routes.py 实时基于当前查询结果计算，不新增字段、不落库
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_customers.html、PROJECT_MEMORY.md
- 修改原因：用户需要在昵称视图和别名视图中快速看到四个平台/店铺的总佣金
- 影响范围：仅发票模块达人/团长昵称管理页面展示；不改 schema
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）
## [2026-04-27 12:22] 修改记录
- 修改内容：发票上传解析新增发票类型与税率/征收率
  - invoice 表新增 invoice_type、tax_rate 两列，保存发票类型和税率/征收率
  - pdf_parser.py 新增解析：发票类型归一为“普通发票”或“增值税专用发票”；税率/征收率保存为文本（如 1%、6%、免税、不征税）
  - 发票复核页新增“发票类型”下拉框和“税率/征收率”输入框，允许人工修正
  - 发票确认入库时写入 invoice_type、tax_rate
  - 发票列表新增类型、税率两列，并纳入前端关键字筛选
  - 样本验证：普票样本解析为 普通发票 + 1%；专票样本解析为 增值税专用发票 + 6%
- 修改文件：
  - 修改：invoicing/pdf_parser.py、invoicing/routes.py、templates/invoicing_invoices_review.html、templates/invoicing_invoices.html、PROJECT_MEMORY.md
  - 数据库：data/main.db（invoice 表新增 invoice_type、tax_rate）
  - 备份：data/main_backup_before_invoice_type_tax_rate_20260427_122002.db
- 修改原因：发票可用性和后续统计需要区分普通发票/增值税专用发票，并记录税率或征收率
- 影响范围：仅发票模块上传解析、复核入库和列表展示；旧 pending 解析文件不保留，重新上传后按新字段解析
- 是否涉及数据库：是（invoice 表新增 2 列）
- 是否需要回滚：否（如需恢复可用备份库覆盖并 git revert 文件改动）
## [2026-04-27 13:15] 修改记录
- 修改内容：发票复核入库的达人/团长匹配逻辑调整
  - 发票复核页“开票主体”改为“按平台/店铺筛选达人/团长”，该字段只用于筛选候选昵称，不作为发票归属写入 invoice.entity_id
  - 发票复核页“客户（达人/团长）”改为“匹配达人/团长昵称”，允许选择具体昵称，也允许保持暂不匹配
  - 达人/团长下拉选项改为显示：昵称 ｜ 平台/店铺 ｜ 应开金额 ｜ 别名
  - 候选昵称按 customer.platform 与筛选的平台/店铺匹配，选择香娜露儿时只展示香娜露儿平台下的昵称及金额
  - 发票确认入库时保存 customer_id；entity_id 在该流程中保持 NULL，避免把筛选条件误当实际入库归属
  - 发票列表的“仅未匹配”改为只判断 customer_id 是否为空；列表文案改为“达人/团长昵称”，不再展示主体列
  - 后续统计时应以 customer_id 对应昵称为事实基础，如存在别名则在查询层按别名归并
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_invoices_review.html、templates/invoicing_invoices.html、PROJECT_MEMORY.md
- 修改原因：发票入库时应匹配具体达人/团长昵称，平台/店铺只用于缩小候选范围；归属到别名应在统计 SQL 层动态完成
- 影响范围：发票复核入库、发票列表补匹配；不改 schema
- 是否涉及数据库：否（用户操作入库时仍会写 invoice.customer_id）
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 13:24] 修改记录
- 修改内容：发票复核页备注解析边界与平台筛选修正
  - invoicing/pdf_parser.py 调整 PDF 备注栏提取边界，遇到购买方/购方/销售方地址、开户银行等字段时停止，避免把购买方与购方信息误吞进备注
  - templates/invoicing_invoices_review.html 将“按平台/店铺筛选达人/团长”从隐藏 option 改为按平台重建下拉选项，修复选择“快手”等平台时仍显示全部达人/团长的问题
  - 复测两份样本 PDF：购买方、销售方可正常解析，备注不再包含购买方地址/购方银行等边界外文本
- 修改文件：
  - 修改：invoicing/pdf_parser.py、templates/invoicing_invoices_review.html、PROJECT_MEMORY.md
- 修改原因：发票复核阶段需要准确区分备注栏与购买方/购方信息；平台筛选必须真正限制达人/团长候选范围
- 影响范围：仅发票 PDF 解析与复核页前端筛选；不改数据库 schema，不影响应开金额导入
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 13:37] 修改记录
- 修改内容：发票备注栏解析范围还原为完整捕获
  - invoicing/pdf_parser.py 的 _extract_pdf_remark 把 stop_prefixes 从 7 项还原为单项 ('开票人',)
  - 之前 13:24 误把"销售方地址 / 购方开户银行 / 销方开户银行"等行视为备注边界外字段而提前截断，实际它们是备注栏内的合法内容（销售方信息通常就写在备注栏里）
  - 用户要求备注内容完整解析进字段文本框
  - 复测两份样本 PDF：样本 1 备注完整捕获销售方地址+电话+开户银行+账号 4 行；样本 2 备注为空（与 PoC 原结果一致）
- 修改文件：invoicing/pdf_parser.py、PROJECT_MEMORY.md
- 修改原因：恢复完整备注捕获，避免误截断
- 影响范围：仅发票 PDF 解析的备注字段；其他字段、模块、DB 都不动
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 14:56] 修改记录
- 修改内容：清空 expected_amount 表全部数据（用户决定全删重导）
  - DELETE FROM expected_amount（清空 1148 行）
  - DELETE FROM sqlite_sequence WHERE name='expected_amount'（重置自增 id，下次 INSERT 从 1 开始）
  - 用户上一轮导入仍有数据问题，且已手工修正源 Excel（含负值改正值），决定全表清空重导
  - 同时保留 customer (965)、customer_alias (2)、invoice (0)、billing_entity (4) 全部不动
  - 操作流程沿用 14:25/14:30 方案：备份 → /tmp 副本 DELETE → cp 覆写回 data/main.db → truncate journal
- 修改文件：data/main.db；备份：data/main_backup_before_clear_expected_amount_20260427_065618.db
- 修改原因：用户已手工修正源 Excel 数据，需要清空表后重新一次性导入
- 影响范围：仅 expected_amount 表数据与自增序列；其他业务表完全未动
- 是否涉及数据库：是（清空业务数据）
- 是否需要回滚：否（如需恢复用 main_backup_before_clear_expected_amount_20260427_065618.db）

## [2026-04-27 14:30] 修改记录
- 修改内容：删除 14:28:08 批次错误的应开金额导入数据（用户重新导入再次错误）
  - DELETE FROM expected_amount WHERE created_at = '2026-04-27 14:28:08'
  - 删除 424 行，金额合计 ¥4,476,579.51（与 14:12:43 那批数字一致，应是同一份错误源数据再次导入）
  - 该批次未自动新建 customer/customer_alias
  - 删除前后基线：expected_amount 1572 → 1148；customer 965（未动）；customer_alias 2（未动）；invoice 0（未动）；billing_entity 4（未动）
  - 操作流程沿用 14:25 方案：备份 → /tmp 副本上 DELETE → cp 覆写回 data/main.db → truncate journal
  - 残留批次：14:02（235 行 ¥-1,585,217.66 注意负值）、14:07（76 行 ¥506,944.69）、14:10（492 行 ¥4,456,500.87）
- 修改文件：data/main.db；备份：data/main_backup_before_delete_batch_20260427_142808_063056.db
- 修改原因：用户上一次导入仍有错，再次需要清理后重新导入
- 影响范围：仅 expected_amount 表中 14:28:08 那一秒的 424 行；其他表/批次完全未动
- 是否涉及数据库：是
- 是否需要回滚：否（如需恢复用 main_backup_before_delete_batch_20260427_142808_063056.db）

## [2026-04-27 14:25] 修改记录
- 修改内容：删除 14:12:43 批次错误的应开金额导入数据
  - 用户反馈 2026-04-27 14:12:43 批次的应开金额导入有错，需删除以便重新导入
  - DELETE FROM expected_amount WHERE created_at = '2026-04-27 14:12:43'
  - 删除 424 行，金额合计 ¥4,476,579.51
  - 该批次未自动新建 customer/customer_alias（同分钟内 0/0），无需级联清理
  - 14:10 那批 492 行（¥4,456,500.87）保留，未动
  - 删除前后基线对比：expected_amount 1572 → 1148；customer 965（未动）；customer_alias 2（未动）；invoice 0（未动）
  - 操作流程：备份 main.db → 因沙箱挂载（virtiofs）不允许删 journal 导致首次 BEGIN/COMMIT 失败，遗留 hot journal → 用 pre-delete 备份恢复 + truncate journal → 改在 /tmp 本地副本上执行 DELETE → cp 覆写回 data/main.db → truncate journal → 验证读取正常
- 修改文件：data/main.db；备份：data/main_backup_before_delete_batch_20260427_141243_061905.db
- 修改原因：用户需要重新导入该批次应开金额
- 影响范围：仅 expected_amount 表中 14:12:43 那一秒的 424 行；其他表/批次完全未动
- 是否涉及数据库：是（DELETE 业务数据）
- 是否需要回滚：否（如需恢复用 main_backup_before_delete_batch_20260427_141243_061905.db 覆盖即可）

## [2026-04-27 13:50] 修改记录
- 修改内容：发票备注解析改为「价税合计 / 开票人」上下界包夹策略
  - invoicing/pdf_parser.py 的 _extract_pdf_remark 重写：以包含「价税合计」的行为上界、以「开票人」开头的行为下界，收集中间所有非空、非单字"备""注"的内容；遇 "注 " 或 "备 " 前缀则剥离
  - 修复 13:37 留下的漏洞：之前以"备"字单行作起点，遗漏了 pdfplumber 提取顺序中出现在"备"字之前的购买方地址/购方开户银行 2 行
  - 复测样本 1：完整捕获 4 行（购买方地址+购方开户银行+销售方地址+销方开户银行）
  - 复测样本 2：备注为空（PDF 本身备注栏只有"备""注"占位，无实际内容）
- 修改文件：invoicing/pdf_parser.py、PROJECT_MEMORY.md
- 修改原因：pdfplumber 表格提取时备注栏左侧"备 注"二字被拆成单字单行，右侧内容会被跨越分布；只用"备"作起点会漏行
- 影响范围：仅发票 PDF 解析的备注字段；不影响其他字段、模块或 DB schema
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 16:33] 修改记录
- 修改内容：发票复核页达人/团长候选筛选增强
  - 发票复核页在“按平台/店铺筛选达人/团长”下方新增关键词筛选框，可按昵称、平台、金额、别名等文本继续缩小候选范围
  - 匹配达人/团长候选排序调整为：同平台下有别名的记录优先，其次按应开金额从大到小，再按昵称排序
  - 前端筛选逻辑在平台筛选基础上叠加关键词筛选，避免候选昵称过多时难以定位
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_invoices_review.html、PROJECT_MEMORY.md
- 修改原因：发票复核入库时达人/团长候选量较大，需要先按平台缩小范围，再用关键词快速定位具体昵称或别名
- 影响范围：仅发票复核页候选下拉展示与前端筛选；不改数据库 schema，不影响发票解析字段
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 16:53] 修改记录
- 修改内容：发票复核页达人/团长候选按账期分行显示
  - 查询 expected_amount.period 字段，候选下拉新增“期间”展示
  - 复核页候选从按 customer_id 聚合改为按 customer_id + platform + period 聚合，避免同一昵称跨账期金额被压成一行
  - 下拉文本改为：昵称 ｜ 平台/店铺 ｜ 期间 ｜ 应开金额 ｜ 别名
  - 验证“新西兰兔子Eva”可同时显示“25年34季度 ¥2186.50”和“26年1季度 ¥811.40”
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_invoices_review.html、PROJECT_MEMORY.md
- 修改原因：发票复核匹配时需要区分同一达人/团长在不同账期的应开金额，避免筛选后缺失当前账期候选
- 影响范围：仅发票复核页候选展示；发票入库仍保存 customer_id，不新增字段
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 16:57] 修改记录
- 修改内容：修复发票复核页账期候选漏改
  - 修正 /invoicing/invoices/review/<pending_id> 页面使用的候选 SQL，将其同步改为按 customer_id + platform + period 聚合
  - 修复复核页下拉仍显示“未设期间”并合并多账期金额的问题
  - 验证“新西兰兔子Eva ｜ 澳柯 ｜ 26年1季度 ｜ 811.40”和“25年34季度 ｜ 2186.50”均可在复核页候选 HTML 中出现
- 修改文件：
  - 修改：invoicing/routes.py、PROJECT_MEMORY.md
- 修改原因：上一版只改到列表页候选 SQL，复核页实际使用的 SQL 漏改，导致用户手测仍看到合并后的旧结果
- 影响范围：仅发票复核页候选展示；不改数据库 schema
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 17:09] 修改记录
- 修改内容：发票匹配增加别名归属与全平台筛选
  - invoice 表新增 alias_name 可空字段，用于保存发票人工匹配的别名归属（别名作为归并标签保存文本，不绑定某一条 customer_alias.id）
  - 发票复核页“按平台/店铺筛选达人/团长”新增“全部平台/店铺”选项，配合关键词可跨平台查找昵称和金额
  - 发票复核页在昵称下拉下方新增“匹配别名”下拉，数据来自已有 customer_alias.alias，并按 alias + platform + period 汇总显示金额和昵称数量
  - 关键词筛选同时作用于昵称候选和别名候选；平台筛选为“全部”时可显示所有平台/店铺结果
  - 发票确认入库时写入 invoice.alias_name；发票横表新增“别名”列，可像昵称一样修改/取消别名匹配
  - “仅未匹配”列表改为同时要求 customer_id 为空且 alias_name 为空，已匹配别名的发票不再算未匹配
- 修改文件：
  - 修改：data/main.db、invoicing/routes.py、templates/invoicing_invoices_review.html、templates/invoicing_invoices.html、PROJECT_MEMORY.md
  - 备份：data/main_backup_before_invoice_alias_20260427_170700.db
- 修改原因：实际开票名称可能无法稳定匹配具体昵称，别名作为归并标签比强行绑定单一昵称更可靠
- 影响范围：发票复核入库与发票列表匹配；后续统计可优先按 alias_name 归并，再回落到 customer_id
- 是否涉及数据库：是（invoice 表新增 alias_name 列）
- 是否需要回滚：否（如需恢复可用备份库覆盖并 git revert 文件改动）

## [2026-04-27 19:30] 修改记录
- 修改内容：发票复核页别名候选拆分到具体昵称并过滤 0 金额
  - 匹配别名下拉从按 alias + platform + period 合并金额，改为按 alias + 具体昵称 + platform + period 分行显示
  - 别名候选显示格式改为：别名 ｜ 昵称 ｜ 平台/店铺 ｜ 期间 ｜ 应开金额，避免同一别名下多个昵称金额合并后无法精确选择
  - 昵称候选和别名候选都改为仅使用 expected_amount.amount <> 0 的记录，过滤掉 0 金额导致的“未设期间/0.00”候选
  - 验证“中青”别名可拆分显示中青旅游 ¥2518.76、中青甄选 ¥1581.09 等具体昵称行，且页面 HTML 不再包含 0.00 候选
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_invoices_review.html、PROJECT_MEMORY.md
- 修改原因：发票匹配需要精确对应具体应开金额，0 金额导入行不应参与候选匹配
- 影响范围：仅发票复核页候选展示；不改数据库 schema，不影响已入库发票
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 19:45] 修改记录
- 修改内容：发票复核候选显示已开发票扣减后的剩余金额
  - 匹配达人/团长昵称候选新增“应开/剩余”展示，剩余 = 当前昵称当前账期应开金额 - 已匹配该昵称且 is_usable=1 的发票金额
  - 匹配别名候选新增“应开/剩余”展示，剩余 = 当前别名 + 当前昵称 + 当前账期应开金额 - 已匹配同别名同昵称且 is_usable=1 的发票金额
  - 扣减按 expected_amount.period_start/period_end 与 invoice.invoice_date 进行账期范围匹配
  - 排序改为按剩余金额从大到小，方便优先看到仍需匹配的候选
  - 临时事务验证：中青/中青旅游/澳柯/25年34季度插入同额测试发票后，剩余从 2518.76 变为 0.00，随后回滚不污染真实库
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_invoices_review.html、PROJECT_MEMORY.md
- 修改原因：下拉金额仅作辅助匹配，但扣减已开发票后更能提示当前候选是否还需要继续匹配
- 影响范围：仅发票复核页候选展示；不改数据库 schema，不影响实际入库逻辑
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 19:59] 修改记录
- 修改内容：取消发票开票日期与佣金周期的扣减关联
  - 检查确认发票复核页“剩余金额”扣减逻辑中曾使用 invoice.invoice_date 与 expected_amount.period_start/period_end 做范围匹配
  - 按用户确认，开票时间不应与佣金周期绑定，已删除候选扣减 SQL 中的 invoice_date >= period_start / invoice_date <= period_end 条件
  - 复核页昵称候选补齐 remaining_total/invoiced_total 字段，避免模板缺字段时显示异常
  - 当前剩余金额按同昵称或同别名已开发票总额扣减，不再按开票日期判断所属佣金周期
  - 验证“阿威在澳洲”已开发票 20000 元会从其澳柯候选剩余中扣除，且不再因 2026-04-24 开票日期排除
- 修改文件：
  - 修改：invoicing/routes.py、PROJECT_MEMORY.md
- 修改原因：实际开票时间与佣金归属周期没有强关联，按日期扣减会误导匹配
- 影响范围：仅发票复核页候选剩余金额展示；不改数据库 schema
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 20:58] 修改记录
- 修改内容：发票列表横表增加点击列头排序
  - templates/invoicing_invoices.html 表头改为可点击排序，支持 ID、发票号、日期、类型、税率、金额、销售方、购买方、项目、达人/团长昵称、别名、可用等列
  - 为每行增加专用 data-* 排序值，避免达人/团长昵称和别名下拉框的全部选项干扰排序
  - 达人/团长昵称、别名两列排序时，未匹配记录固定排在名称排序之前，方便优先处理空归属
  - 保留原有前端关键字筛选，排序后继续按当前筛选条件更新显示数量
- 修改文件：
  - 修改：templates/invoicing_invoices.html、PROJECT_MEMORY.md
- 修改原因：发票列表需要更快定位、核查和优先处理未匹配记录
- 影响范围：仅发票列表前端交互；不改数据库 schema 和后端入库逻辑
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 21:07] 修改记录
- 修改内容：达人/团长昵称列表增加点击列头排序
  - templates/invoicing_customers.html 的昵称列表横表支持点击“达人/团长昵称、澳柯佣金、香娜露儿佣金、快手佣金、幕莲蔓佣金”列头排序
  - 为昵称列表每行增加 data-* 排序值，金额列按数字排序，昵称列按中文文本排序
  - 保留原有关键词筛选与全选批量设置别名逻辑，排序后继续按当前筛选条件更新显示数量
- 修改文件：
  - 修改：templates/invoicing_customers.html、PROJECT_MEMORY.md
- 修改原因：达人/团长昵称横表需要按昵称或各平台佣金快速排序查看
- 影响范围：仅达人/团长昵称管理页前端交互；不改数据库 schema 和后端 CRUD
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 21:16] 修改记录
- 修改内容：应开 vs 已开核对页改为平台/店铺汇总口径
  - 未匹配 banner 文案从“客户或主体”改为“达人/团长或别名”
  - 未匹配统计条件改为 customer_id 为空且 alias_name 为空，修复仅 1 张未匹配但旧口径显示 83 张的问题
  - 主表从 customer × entity 维度改为四个平台/店铺固定行：澳柯、香娜露儿、快手、幕莲蔓
  - 应开金额按 expected_amount.platform 汇总；已开金额按发票匹配昵称 customer.platform 汇总，并对别名可唯一推断平台的发票做平台归属
  - 增加“已匹配但无法确定平台/店铺”提示，用于只匹配跨平台别名但未匹配具体昵称的发票
  - 页面保留日期筛选、总计应开/已开/差额、前端关键字筛选
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_reconciliation.html、PROJECT_MEMORY.md
- 修改原因：核对页核心口径应围绕店铺/平台的应开与已开发票金额，而不是旧版主体/客户组合
- 影响范围：仅发票核对汇总页；不改数据库 schema 和发票入库逻辑
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 22:46] 修改记录
- 修改内容：核对页支持转移开票承接口径
  - 已开发票保留佣金归属平台/店铺，同时额外按购买方平台/店铺生成“转移开票”明细
  - 当发票归属平台/店铺与购买方平台/店铺不同，例如快手佣金开票至澳柯，该发票同时出现在快手归属明细和澳柯“转移开票”承接明细中
  - 澳柯已开金额会包含转移承接发票，用于缩小澳柯作为购买方的差额
  - 转移明细显示为：别名=转移开票，昵称列=来源：<归属平台/店铺> / <昵称或别名>
  - 验证快手发票 26332000003353345956（¥42705.56，购买方澳柯）在澳柯展开明细中显示“来源：快手 / 紫烟海外优选”，并保留 PDF 链接
- 修改文件：
  - 修改：invoicing/routes.py、PROJECT_MEMORY.md
- 修改原因：转移开票既应体现为来源平台/店铺的佣金已开，也应体现为购买方平台/店铺的开票承接
- 影响范围：仅应开 vs 已开核对页统计和明细展示；不改数据库 schema
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 21:26] 修改记录
- 修改内容：应开 vs 已开核对页增加平台/店铺明细展开表
  - 点击汇总横表中的平台/店铺名称（澳柯、香娜露儿、快手、幕莲蔓）可在该行下方展开明细表
  - 明细表字段：别名、昵称或昵称合集、应开金额、已开金额、余额
  - 应开明细按平台 + 别名归并；无别名时按单个昵称显示
  - 已开明细按发票匹配到的别名/昵称归并；有别名时显示该别名下昵称合集
  - 保留顶部平台汇总、日期筛选和前端关键字筛选
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_reconciliation.html、PROJECT_MEMORY.md
- 修改原因：平台总额需要可下钻到具体别名/昵称层，方便核对余额来源
- 影响范围：仅发票核对页展示与前端交互；不改数据库 schema
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 22:07] 修改记录
- 修改内容：核对页平台明细增加未匹配标识与发票 PDF 链接
  - 平台/店铺展开明细中，真正未匹配发票行的昵称列显示“未匹配 <金额>”，例如“未匹配 1162.00”
  - 未匹配发票按 buyer_name 中的平台/店铺关键词归入对应平台明细
  - 明细表“已开金额”变为可点击项，点击后展开该归并项下所有发票链接
  - 发票链接显示“发票号 / 金额”，点击后打开对应 PDF
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_reconciliation.html、PROJECT_MEMORY.md
- 修改原因：核对平台明细时需要看到未匹配金额来源，并能直接打开构成已开金额的发票 PDF
- 影响范围：仅应开 vs 已开核对页展示与交互；不改数据库 schema
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 22:16] 修改记录
- 修改内容：核对页明细修正未匹配重复行并增加应开组成展开
  - 修复平台明细中未匹配发票被额外追加成第二行的问题，改为在原有已开明细行的昵称列显示“未匹配 <金额>”
  - 应开金额列改为可点击展开，显示组成该应开金额的导入周期和金额（如“26年1季度 / ¥811.40”）
  - 已开金额列保留可点击展开 PDF 链接
  - 验证核对页 HTML 中未匹配 1162.00 只对应同一条明细行，同时应开/已开展开控件均存在
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_reconciliation.html、PROJECT_MEMORY.md
- 修改原因：平台明细应避免重复展示同一未匹配发票，并需要下钻查看应开金额由哪些导入周期/金额构成
- 影响范围：仅应开 vs 已开核对页展示与交互；不改数据库 schema
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 21:33] 修改记录
- 修改内容：移除核对页“已匹配但无法确定平台/店铺”提示
  - templates/invoicing_reconciliation.html 删除第二行 banner：跨平台别名但未匹配具体达人/团长昵称的提示
  - 保留真正未匹配达人/团长或别名的第一行提示
  - 后端仍保留相关统计变量，页面暂不展示，避免干扰当前以余额核对为主的工作流
- 修改文件：
  - 修改：templates/invoicing_reconciliation.html、PROJECT_MEMORY.md
- 修改原因：当前目标是确认达人/团长或别名还需开票余额，不要求每张发票精确拆配到多笔佣金；该提示容易造成误导
- 影响范围：仅核对页提示文案展示；不改数据库 schema 和统计主表
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 21:44] 修改记录
- 修改内容：核对页已开发票平台归属增加购买方名称兜底
  - 已开发票平台/店铺归属顺序调整为：invoice.platform → 匹配昵称 customer.platform → 别名唯一可推断平台 → buyer_name 包含平台/店铺名
  - buyer_name 包含“澳柯/香娜露儿/快手/幕莲蔓”时，分别归入对应平台
  - 修复 5 张只匹配跨平台别名“罐头”的发票无法归入平台的问题；因购买方均为“上海澳柯保健品有限公司”，现归入澳柯
  - 验证可用发票平台汇总变为：澳柯 82 张、快手 1 张，未确定平台降为 0
- 修改文件：
  - 修改：invoicing/routes.py、PROJECT_MEMORY.md
- 修改原因：发票购买方/开票对象可作为平台/店铺归类依据，尤其适用于只匹配跨平台别名但未匹配具体昵称的发票
- 影响范围：仅应开 vs 已开核对页的已开金额平台归属；不改数据库 schema 和发票原始记录
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 21:57] 修改记录
- 修改内容：发票列表增加可用筛选与单张匹配页
  - 发票列表导航新增“仅可用 / 仅不可用”筛选
  - 不可用发票行新增“设为可用”按钮，可直接把 is_usable 改为 1
  - 发票列表横表移除达人/团长昵称与别名的超长下拉，只显示当前匹配结果和“匹配/修改”入口
  - 新增单张发票匹配页 /invoicing/invoices/<id>/match，支持平台/店铺筛选、关键词筛选、达人/团长昵称匹配、别名匹配、可用状态切换
  - 临时库验证：POST 设置 id=88 的 is_usable=1 成功，真实库未被测试污染
- 修改文件：
  - 新增：templates/invoicing_invoice_match.html
  - 修改：invoicing/routes.py、templates/invoicing_invoices.html、PROJECT_MEMORY.md
- 修改原因：发票列表内长下拉难以实际操作；不可用发票需要可快速恢复为可用
- 影响范围：发票列表与单张发票匹配流程；不改数据库 schema
- 是否涉及数据库：否（用户操作时会更新 invoice.customer_id / alias_name / is_usable）
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 23:16] 修改记录
- 修改内容：应开 vs 已开核对页拆分归属开票 / 转移入开票 / 转移出开票
  - invoicing/routes.py 新增核对计算逻辑：同时识别达人/团长所属平台（归属平台）与发票购买方平台（开票对象平台）
  - 平台/店铺主表已开金额改为：归属开票 + 转移入开票；转移出开票仅在明细中提示，不额外加减差额
  - 平台明细新增三类可展开 PDF 链接：归属开票、转移入开票、转移出开票
  - 紫烟海外优选示例：在快手明细中显示归属开票与转移出至澳柯；在澳柯明细中显示来源快手的转移入开票
  - 应开金额明细保留按导入期间/金额展开，便于核对余额来源
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_reconciliation.html、PROJECT_MEMORY.md
- 修改原因：跨平台/店铺开票需要同时表达“佣金归属”和“实际购买方开票对象”，避免把转移开票误算为某一侧单一归属
- 影响范围：仅应开 vs 已开核对页展示与汇总口径；不改数据库 schema 和原始发票/应开金额数据
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-27 23:48] 修改记录
- 修改内容：核对页转移开票口径细化与列宽修正
  - 真正未匹配发票只统计 customer_id 为空且 alias_name 为空的记录；当前验证为 1 张、金额 1162.00
  - 仅匹配别名但无法确定归属平台的发票，不再并入“未匹配”明细；改按购买方平台/店铺落到对应别名行
  - 转移出开票不再计入来源平台的“合计已开”，只作为“转移出抵减”减少余额
  - 快手示例：紫烟海外优选开给澳柯的 42705.56 在快手显示为转移出抵减，快手合计已开为 0，余额仍扣减该金额
  - 核对页主表和展开明细改为固定列宽，缓解长昵称/长别名导致的列挤压
  - 复核澳柯口径：购买方为澳柯的可用发票 83 张，金额合计 3919482.46，与澳柯核对行合计已开一致
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_reconciliation.html、PROJECT_MEMORY.md
- 修改原因：转移开票应体现“开给谁”和“抵减谁”两层含义；不能把转移出误算成来源平台已开金额，也不能把已匹配别名的发票误列为未匹配
- 影响范围：仅应开 vs 已开核对页展示与汇总口径；不改数据库 schema 和原始数据
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-28 13:18] 修改记录
- 修改内容：修复发票匹配页同名别名跨平台回显错误
  - 发票匹配页的“匹配别名”下拉提交值由单纯 alias 文本改为 customer_id + alias 组合
  - 保存别名匹配时同时写入 invoice.customer_id 与 invoice.alias_name，避免“罐头”等跨平台同名别名重新进入页面后漂移到其他平台/店铺
  - 发票上传解析后的复核入库页同步采用同样的别名提交规则，避免新入库发票出现同类问题
  - 前端交互调整：选择具体达人/团长昵称时清空别名选择；选择别名时清空昵称选择，避免双重提交含义冲突
  - 临时库验证：提交 92::罐头 后保存为 customer_id=92、alias_name=罐头；真实库未被测试写入
- 修改文件：
  - 修改：invoicing/routes.py、templates/invoicing_invoice_match.html、templates/invoicing_invoices_review.html、PROJECT_MEMORY.md
- 修改原因：alias_name 本身不是唯一键，同一别名可出现在多个平台/店铺；仅保存别名文本无法还原用户选择的具体归属
- 影响范围：发票单张匹配页与上传复核入库页；不改数据库 schema
- 是否涉及数据库：否（仅用户保存匹配时会按新规则写入 invoice.customer_id / alias_name）
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-28 13:35] 修改记录
- 修改内容：发票匹配下拉的余额显示改为“匹配后余额”
  - 单张发票匹配页中，达人/团长昵称和别名下拉显示由“剩余”改为“匹配后”
  - “匹配后”计算口径为：该行应开金额 - 当前这张发票金额；超过应开金额时显示负数
  - 发票上传解析后的复核入库页同步采用同一显示逻辑
  - 验证：发票 26352000000982919761 匹配页出现“匹配后”且可显示负数；页面中不再出现“剩余”字样
- 修改文件：
  - 修改：templates/invoicing_invoice_match.html、templates/invoicing_invoices_review.html、PROJECT_MEMORY.md
- 修改原因：匹配下拉用于辅助判断“当前发票选中该行后还差多少”，历史剩余与应开相等时没有判断价值
- 影响范围：仅发票匹配/复核页面的下拉展示文本与计算口径；不改数据库 schema 和保存逻辑
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-28 13:45] 修改记录
- 修改内容：发票匹配下拉按“匹配后金额”排序
  - 单张发票匹配页中，达人/团长昵称与别名下拉按“应开金额 - 当前发票金额”升序排列
  - 发票上传解析后的复核入库页同步采用同一排序
  - 负数（发票金额超过该行应开金额）会排在前面，随后是最接近 0 的候选，便于快速判断
  - 验证：/invoicing/invoices/91/match 返回 200，页面正常显示“匹配后”
- 修改文件：
  - 修改：invoicing/routes.py、PROJECT_MEMORY.md
- 修改原因：匹配下拉应优先展示最接近当前发票金额的候选项，减少长列表查找成本
- 影响范围：仅发票匹配/复核页面的候选排序；不改数据库 schema 和保存逻辑
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）

## [2026-04-28 15:43] 修改记录
- 修改内容：核对页明细长链接允许换行
  - templates/invoicing_reconciliation.html 调整应开金额明细与发票链接 CSS
  - 长周期/金额列表和长发票号链接允许在单元格内换行，避免横向撑开页面
  - 验证：/invoicing/reconciliation 返回 200，页面 CSS 已包含 overflow-wrap:anywhere
- 修改文件：
  - 修改：templates/invoicing_reconciliation.html、PROJECT_MEMORY.md
- 修改原因：应开 vs 已开核对明细中长列表不应横向溢出，需保持表格可读
- 影响范围：仅核对页明细链接展示；不改后端逻辑和数据库
- 是否涉及数据库：否
- 是否需要回滚：否（如出问题 git revert 文件改动）
## [2026-04-30 11:32] 修改记录
- 修改内容：在应开 vs 已开核对页新增“别名/昵称汇总”区块，支持按别名或昵称关键词筛选，跨平台/店铺合并显示应开总计、已开票总计、发票张数与余额，并支持展开查看应开明细、已开明细和各平台余额明细。
- 修改文件：invoicing/routes.py；templates/invoicing_reconciliation.html；PROJECT_MEMORY.md
- 修改原因：需要直接按别名或昵称核对其跨平台应开与已开金额，并在合并视图下保留平台/店铺来源与余额去向。
- 影响范围：仅发票核对页展示与统计口径；不改数据库 schema 和原始发票数据。
- 是否涉及数据库：否
- 是否需要回滚：否
## [2026-04-30 11:50] 修改记录
- 修改内容：修正应开 vs 已开核对页展开明细显示，去除金额前的异常“楼/¥”字符；上方平台明细和下方别名/昵称汇总的应开、已开、余额展开内容改为单行显示并支持横向滚动；余额展开明细按正数、负数、零分别套用颜色。
- 修改文件：templates/invoicing_reconciliation.html；PROJECT_MEMORY.md
- 修改原因：展开明细中的异常金额符号和自动换行影响核对阅读，余额明细需要更清晰地区分正负状态。
- 影响范围：仅发票核对页展示样式与金额文本展示；不改后端统计逻辑和数据库。
- 是否涉及数据库：否
- 是否需要回滚：否
## [2026-04-30 12:07] 修改记录
- 修改内容：发票列表将最左侧 ID 改为选择框，并新增“下载发票到桌面”按钮；支持按所选发票把 PDF 复制到桌面，并按“不能使用前缀 + 金额 + 昵称 + 发票号码 + 平台店铺名称 + 账单周期 + 普票/专票税率”规则重命名。
- 修改文件：invoicing/routes.py；templates/invoicing_invoices.html；PROJECT_MEMORY.md
- 修改原因：批量导出发票时，ID 列无业务价值，需要更直接的勾选与按规则落地到本地桌面的能力。
- 影响范围：仅发票列表页展示、交互和 PDF 导出流程；不改数据库 schema。
- 是否涉及数据库：否
- 是否需要回滚：否
## [2026-04-30 12:22] 修改记录
- 修改内容：发票列表批量下载改为浏览器直接下载 ZIP，不再尝试写入服务器桌面；ZIP 内每个 PDF 按新命名规则生成，并新增“开票平台与归属平台不一致时追加开票平台关键字”的判断。
- 修改文件：invoicing/routes.py；templates/invoicing_invoices.html；PROJECT_MEMORY.md
- 修改原因：VPS 部署场景下服务器无法直接写入用户本机桌面，需改为浏览器可接收的下载方式；同时补齐新的命名规则。
- 影响范围：仅发票列表批量下载行为与文件命名；不改数据库 schema。
- 是否涉及数据库：否
- 是否需要回滚：否

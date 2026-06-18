## [2026-06-13 16:02] 修改记录
- 修改内容：修复快递费账单核查勾选与修正链路。前端新增按账单行 ID 持久保存勾选状态，切换全部/价格异常/空白异常/重量异常/已核查标签、排序、翻页、搜索时已勾选行不丢失；OPT_07、下载修正文件、正式入库均提交同一份勾选清单。后端将勾选行视为正确数据，清除修正标记并保留原始费用；未勾选的价格异常、空白异常、重量异常写入 `corrected_fee` 并标记已修正。下载修正 ZIP 前会先按当前勾选清单生成修正记录；正式入库前再次按当前勾选清单复核，并将已修正行的 `actual_fee` 写成 `corrected_fee`，同时把核对结果置为正确。快递费汇总表下载从单个 xlsx 改为 ZIP，ZIP 内包含原汇总 Excel。
- 修改文件：courier_fee/bill_services.py；courier_fee/routes.py；templates/courier_fee.html；PROJECT_MEMORY.md
- 修改原因：用户明确要求勾选行无论系统异常判断如何都按正确数据保留，未勾选异常行必须在修正文件和正式入库数据表中使用修正后的正确数值，并希望汇总表以 ZIP 下载。
- 影响范围：仅影响快递费账单模块的异常勾选、修正 ZIP、正式入库写回和汇总表下载格式；不修改数据库结构，不影响底单导入、计费规则和其他业务模块。
- 是否涉及数据库：否（代码不改表结构；正式入库功能运行时会按业务要求更新快递账单行费用）
- 是否需要回滚：是

## [2026-06-13 15:23] 修改记录
- 修改内容：将页头打印 WPS 日期口径修复与快递费汇总导出功能提交并推送到 GitHub `main`，业务提交为 `051d42a`；随后在西班牙马德里服务器 `208.85.17.83` 的 `/root/my-flask-project` 执行 `git pull origin main` 同步到该提交并重启 Flask 服务。重启后服务进程监听 `0.0.0.0:5001`，服务器本机 `/`、`/courier_fee/`、`/label_print/` 均返回 302 登录跳转；服务器端自检 `/courier_fee/bill_download_summary_workbook` 路由已注册。
- 修改文件：GitHub `main`；服务器 `/root/my-flask-project`；PROJECT_MEMORY.md
- 修改原因：用户要求上传 GitHub 最新代码并更新西班牙服务器上运行的代码。
- 影响范围：GitHub `main` 与西班牙服务器线上 Flask 应用代码；未修改业务数据库和服务器 `data/` 目录。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-13 15:14] 修改记录
- 修改内容：快递费计算工作台的快递费账单模块新增“生成快递费汇总表”下载按钮，按原 VBA 汇总口径读取当前年月已核查入库账单数据，生成固定格式 Excel，文件名为 `快递费汇总YYYYMM月.xlsx`。汇总表固定 A1:D15 结构，明细 sheet 包含申通抖音、申通微信澳柯、韵达抖音、韵达微信澳柯，默认不包含中通。
- 修改文件：courier_fee/bill_services.py；courier_fee/routes.py；templates/courier_fee.html；PROJECT_MEMORY.md
- 修改原因：用户需要将原 VBA 快递费汇总表生成流程迁移到 Web 工作台，直接基于已核查入库数据生成月度汇总表。
- 影响范围：仅快递费账单模块新增汇总表下载；不影响账单导入、核查、修正、正式入库和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-13 14:56] 修改记录
- 修改内容：修复页头打印 WPS 今日记录读取的业务日期口径，将“今日”从服务器本地时区日期改为北京时间（Asia/Shanghai）日期，避免线上服务器 UTC 时区导致中国当天记录无法被筛出。
- 修改文件：label_print/routes.py；PROJECT_MEMORY.md
- 修改原因：代码部署到线上后服务器使用 UTC 时间，页头打印 WPS 今日记录按 `datetime.now().date()` 判断日期时可能与中国业务日期不一致，导致 WPS 中已有当天记录但页面读取为空。
- 影响范围：仅页头打印模块 WPS 今日记录读取和今日记录列表；不修改 WPS 数据、不修改数据库结构、不扩展历史日期读取功能。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-12 12:07] 修改记录
- 修改内容：将发票核对应开金额导入表头兼容修复提交并推送到 GitHub `main`，业务修复提交为 `547ce05`；随后在西班牙马德里服务器 `208.85.17.83` 的 `/root/my-flask-project` 执行 `git pull origin main` 同步到 GitHub `main` 最新代码，并重启 Flask 服务。重启后服务进程监听 `0.0.0.0:5001`，公网 `/` 与 `/invoicing/expected-amounts` 均返回 302 登录跳转；服务器端自检 `find_header(['达人/客户', '应开金额'], ...)` 返回 `达人/客户` 与 `应开金额`。
- 修改文件：GitHub `main`；服务器 `/root/my-flask-project`；PROJECT_MEMORY.md
- 修改原因：用户要求修复后上传 GitHub，并更新网上运行的代码。
- 影响范围：GitHub `main` 与西班牙服务器线上 Flask 应用代码；未修改业务数据库和服务器 `data/` 目录。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-12 12:02] 修改记录
- 修改内容：修复发票核对应开金额 Excel 导入无法识别佣金导出文件表头的问题。应开金额导入的客户列候选新增 `达人/客户`，使微信小店、抖音香娜露儿、抖音幕莲蔓、快手澳柯佣金汇总 ZIP 内的“应开金额导入.xlsx”在手工填写默认归属、店铺/平台、期间后可正常通过表头校验。
- 修改文件：invoicing/routes.py；PROJECT_MEMORY.md
- 修改原因：4 个佣金模块导出的应开金额导入文件统一使用 `达人/客户`、`应开金额` 两列表头，但发票模块此前只在错误提示中提到“达人/客户”，实际 `CUSTOMER_HEADERS` 未包含该候选，导致上传后报“Excel 缺少达人/客户列或应开金额列”。
- 影响范围：仅影响发票核对模块应开金额 Excel 导入的客户列表头识别；不改变数据库结构、不改变佣金导出金额和文件内容、不影响发票上传、匹配、下载和核对汇总逻辑。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-11 16:29] 修改记录
- 修改内容：西班牙马德里服务器 `208.85.17.83` 从 GitHub `origin/main` 拉取快手澳柯模块最新提交 `be7ab43`，安装新增依赖 `msoffcrypto-tool==6.0.0`（同时安装 `olefile`），并重启 Flask 服务。重启后服务器进程监听 `0.0.0.0:5001`，服务器本机 `/` 与 `/kuaishou_aoke/` 返回 302，公网 `http://208.85.17.83:5001/` 与 `/kuaishou_aoke/` 返回 302；服务器 HEAD 与 `origin/main` 均为 `be7ab43`，快手澳柯路由和订单加密读取依赖自检通过。
- 修改文件：服务器 `/root/my-flask-project`；PROJECT_MEMORY.md
- 修改原因：用户要求登录西班牙服务器，将 GitHub 仓库最新代码拉下并更新线上服务。
- 影响范围：西班牙服务器线上 Flask 应用代码、Python 虚拟环境依赖和运行进程；未覆盖服务器 `data/`，未修改业务数据。服务器工作区仅保留未跟踪日志 `flask.log`。
- 是否涉及数据库：否（仅代码部署、依赖安装和服务重启；未写入业务数据库）
- 是否需要回滚：是（可在服务器 `git reset --hard 1689eee` 或指定旧提交后重新安装依赖并重启服务）

## [2026-06-11 15:49] 修改记录
- 修改内容：快手澳柯模块新增佣金汇总导出和达人/团长明细导出。导出逻辑参考抖音佣金模块：按资金流水表 `实际结算时间` 筛选；达人侧按 `达人ID` 汇总 `达人佣金(元)` 与 `其他收费`，其中 `其他收费/其他收费明细`（如“商城分销信息服务费（授权达人推广)”）归入达人侧，并在达人汇总中单列“其他收费”和“佣金合计”；团长侧按 `团长id` 汇总 `团长佣金(元)`。昵称从订单表映射，达人使用 `CPS达人ID -> CPS达人昵称`，团长使用 `团长ID -> 团长昵称`；同一 ID 多个昵称时按订单表最后一次出现的昵称展示，但统计仍按 1 个 ID 汇总。无法找到 ID 或昵称的记录不混入汇总，单独输出未匹配表并注明原因（缺少达人ID/团长ID、订单表未找到达人昵称/团长昵称）。汇总 ZIP 包含佣金汇总、应开金额导入、未匹配佣金文件；明细 ZIP 按达人/团长拆分并附带未匹配佣金文件。
- 修改文件：kuaishou_aoke/services.py；kuaishou_aoke/routes.py；templates/kuaishou_aoke.html；PROJECT_MEMORY.md
- 修改原因：用户需要按快手澳柯历史 VBA 口径迁移佣金汇总和明细拆分导出，同时处理结算表只有达人/团长 ID、昵称需从订单表匹配，以及“其他收费”归属判断问题。
- 影响范围：仅影响快手澳柯模块的佣金导出新增功能；不改变三表导入、防重、原始数据导出、数据库结构及其他模块。
- 是否涉及数据库：否（只读取 ks_aoke_orders、ks_aoke_fund_flow，不写业务数据）
- 是否需要回滚：是

## [2026-06-11 15:02] 修改记录
- 修改内容：修复快手澳柯订单表防重逻辑。原逻辑在防重字段任一值为空时放弃生成防重键，导致历史订单中 `SKU编码` 为空的记录重复导入；现改为仅当所有防重字段均为空时才放弃防重，单个空字段统一以固定占位符参与防重比较。已用临时数据库验证同一批订单/资金流水/售后连续导入两次时，第二次三表均写入 0 行。按用户要求清空本地 `data/main.db` 中快手澳柯三张业务表数据，并将快手澳柯状态表计数和日期范围归零，方便重新测试。
- 修改文件：kuaishou_aoke/services.py；data/main.db（清空快手澳柯本地测试数据）；PROJECT_MEMORY.md
- 修改原因：用户测试发现快手澳柯订单表重复导入，需修正空字段参与防重的处理方式，并清理本地快手澳柯测试数据后重新验证。
- 影响范围：仅影响快手澳柯模块导入防重逻辑与本地快手澳柯测试数据；不影响微信小店、抖音店铺、发票、快递费等其他模块。
- 是否涉及数据库：是（清空本地 ks_aoke_orders、ks_aoke_fund_flow、ks_aoke_after_sales 数据，并重置 ks_aoke_data_status 状态；不修改其他模块数据）
- 是否需要回滚：是

## [2026-06-11 14:40] 修改记录
- 修改内容：新增快手澳柯模块（kuaishou_aoke），按微信小店三表导入/原始数据处理模式接入订单表、资金流水表、售后表。模块支持订单表加密 Excel 自动读取：检测到 Office 文件加密时使用文件名去扩展名后的最后 6 位作为打开密码解密，再按完整表头导入。三张表均自动建表/补列、导入前校验同批文件列结构、按业务键跳过重复记录、维护当前数据状态，并支持字段选择、日期范围、多条件筛选后导出 Excel。页面不包含佣金导出区块。
- 修改文件：kuaishou_aoke/__init__.py（新增）；kuaishou_aoke/table_schemas.py（新增）；kuaishou_aoke/services.py（新增）；kuaishou_aoke/routes.py（新增）；templates/kuaishou_aoke.html（新增）；app.py；auth/services.py；templates/index.html；requirements.txt；PROJECT_MEMORY.md
- 修改原因：用户需要新增“快手澳柯”独立模块，上传快手订单、资金流水、售后三类表格，并兼容订单表文件名后 6 位密码访问方式；佣金区块下一步再做。
- 影响范围：新增快手澳柯模块及其权限/首页入口；新增数据库表 ks_aoke_orders、ks_aoke_fund_flow、ks_aoke_after_sales、ks_aoke_data_status；不影响微信小店、抖音店铺、发票、快递费等既有模块业务逻辑。
- 是否涉及数据库：是（首次访问/导入时自动创建快手澳柯 3 张业务表和 1 张数据状态表；不修改已有表）
- 是否需要回滚：是

## [2026-06-10 14:29] 修改记录
- 修改内容：发票列表“下载选中发票”生成 ZIP 时，若发票记录已勾选“网上开票”，则 ZIP 内对应 PDF 文件名末尾追加“网传开票”标记。
- 修改文件：invoicing/routes.py；PROJECT_MEMORY.md
- 修改原因：用户需要区分网上开票发票下载文件，便于后续网传开票处理。
- 影响范围：仅影响发票核对模块下载选中发票时 ZIP 内 PDF 文件命名；不影响发票列表展示、网上开票字段保存、PDF 原文件、导出 Excel、发票匹配和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-10 13:18] 修改记录
- 修改内容：修复抖音店铺佣金汇总/明细导出在页面已有日期时仍提示“请选择佣金导出的开始日期和结束日期”的问题。前端佣金导出读取专用日期输入框为空时，会回退读取原始数据处理区的日期；提交时同时带上 `start_date/end_date` 与 `dy_commission_start_date/dy_commission_end_date`。后端导出路由兼容 `start_date/end_date`、`dy_commission_start_date/dy_commission_end_date`、`date_start/date_end` 三组字段名。
- 修改文件：douyin_shop_common/__init__.py；templates/douyin_shop.html；PROJECT_MEMORY.md
- 修改原因：避免浏览器页面状态、字段名或用户实际填写区域不一致时，佣金导出接口收到空日期导致误报缺少日期。
- 影响范围：仅影响香娜露儿（抖音）和幕莲蔓（抖音）的佣金汇总导出与佣金明细导出日期参数读取；不改变佣金计算、ID 列导出、原始数据导入导出和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-10 13:09] 修改记录
- 修改内容：抖音店铺（香娜露儿/幕莲蔓）佣金汇总导出 ZIP 中的“佣金汇总.xlsx”新增 ID 列。达人汇总 sheet 增加“达人ID”，按资金结算表达人名称匹配达人ID；团长汇总 sheet 增加“团长ID”，按招商订单明细出单机构匹配团长活动ID。同一名称对应多个 ID 时使用英文分号 `;` 合并到同一单元格。
- 修改文件：douyin_shop_common/services.py；PROJECT_MEMORY.md
- 修改原因：用户需要在抖音佣金汇总表中同时查看达人/团长名称及对应 ID，便于后续核对与处理。
- 影响范围：仅影响香娜露儿（抖音）和幕莲蔓（抖音）佣金汇总导出 ZIP 内的“佣金汇总.xlsx”；不影响应开金额导入文件、佣金明细 ZIP、原始数据导入导出、数据库结构和其他模块。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-10 12:12] 修改记录
- 修改内容：发票核对模块的发票列表新增“网上开票”列。代码在首次运行时检测 `invoice` 表是否存在 `online_invoice` 列；不存在时自动补列 `INTEGER NOT NULL DEFAULT 0`，已有发票默认“否”。发票列表每条记录显示“网上开票”复选框，点击后按与“已报税”标记一致的方式切换并保存到数据库。
- 修改文件：invoicing/routes.py；templates/invoicing_invoices.html；PROJECT_MEMORY.md
- 修改原因：需要在发票列表中标记每张发票是否属于网上开票，并允许人工维护该状态；线上真实数据库不能手工改表，需由代码首次运行自动迁移。
- 影响范围：仅影响发票核对模块的发票列表展示与 `invoice` 表新增布尔字段；不影响发票 PDF 解析、上传、匹配、下载导出、应开金额与核对汇总逻辑。
- 是否涉及数据库：是（`invoice` 表首次运行自动新增 `online_invoice` 列，默认 0）
- 是否需要回滚：是

## [2026-06-08 20:46] 修改记录
- 修改内容：新建快递费计算模块（courier_fee），完成第一阶段——底单记录导入功能。包含：新建 courier_fee Blueprint（__init__.py / routes.py / services.py / table_schemas.py）；新建 templates/courier_fee.html；注册蓝图至 app.py；首页 index.html 增加"快递费计算"入口按钮（受权限控制）。功能包括：底单记录多文件 Excel 上传导入（去重键：tracking_no；发货时间无效行自动跳过）、分页查询、多条件筛选、全字段导出为 Excel。
- 修改文件：courier_fee/__init__.py（新增）、courier_fee/table_schemas.py（新增）、courier_fee/services.py（新增）、courier_fee/routes.py（新增）、templates/courier_fee.html（新增）、app.py（新增 import + register_blueprint）、templates/index.html（新增菜单入口）
- 修改原因：按用户需求迁移 VBA 快递费计算功能到 Flask 项目，第一阶段先完成底单记录独立导入模块
- 影响范围：新增模块，不影响任何已有模块；数据存储在 courier_fee_shipments 表和 courier_fee_import_status 表
- 是否涉及数据库：是（新增表 courier_fee_shipments、courier_fee_import_status）
- 是否需要回滚：否（新增，不影响原有功能）

## [2026-06-07 16:50] 修改记录
- 修改内容：修正抖音店铺佣金汇总导出 ZIP 中“应开金额导入”文件的金额生成规则。应开金额不再按佣金汇总净额直接取相反数，而是导出佣金汇总净额的绝对值；正常已结算负佣金和结算后退款/保证金退款等正佣金都会在应开金额导入文件中显示为正值。佣金汇总表和明细导出仍保留原始正负口径。
- 修改文件：douyin_shop_common/services.py；PROJECT_MEMORY.md
- 修改原因：抖音资金结算表中 `结算后退款-原路退回`、`保证金退款-支出退回` 等结算单类型的达人佣金/招商服务费可能在佣金列中表现为正值；上一版直接取反会把这类应开金额导出为负数。
- 影响范围：仅影响香娜露儿（抖音）和幕莲蔓（抖音）佣金汇总导出 ZIP 内的应开金额导入 Excel；不影响微信小店、数据库、原始数据导入导出、佣金汇总表和佣金明细 ZIP。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-07 16:35] 修改记录
- 修改内容：调整抖音店铺佣金导出日期默认逻辑。香娜露儿/幕莲蔓佣金汇总与明细导出的开始、结束日期优先使用浏览器记录的上次选择；没有历史选择时，开始和结束日期均默认资金结算表最新日期，不再默认从历史最早日期（如 2025-07）开始。同时复核当前应开金额导入文件符号逻辑，服务器新导出结果已逐行等于佣金汇总净额的相反数。
- 修改文件：templates/douyin_shop.html；PROJECT_MEMORY.md
- 修改原因：佣金导出日期每次回到资金结算表最早日期会误导用户导出全历史范围；应默认用户最近操作日期或最新数据日期。
- 影响范围：仅影响香娜露儿（抖音）和幕莲蔓（抖音）页面佣金导出日期输入框默认值；不影响微信小店、数据库、原始数据导入导出、佣金汇总/明细计算口径。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-07 16:22] 修改记录
- 修改内容：修正抖音店铺（香娜露儿/幕莲蔓）佣金汇总导出 ZIP 中“应开金额导入”文件的金额符号。应开金额改为佣金汇总净额的相反数：原负值导出为正值，原正值导出为负值；佣金汇总表和明细导出保持原口径不变。
- 修改文件：douyin_shop_common/services.py；PROJECT_MEMORY.md
- 修改原因：抖音资金结算表中达人佣金/招商服务费通常以负数表示佣金支出，少量正数表示退款回退；发票应开金额导入需要使用相反方向的金额。
- 影响范围：仅影响香娜露儿（抖音）和幕莲蔓（抖音）佣金汇总导出 ZIP 内的应开金额导入 Excel；不影响微信小店、数据库、原始数据导入导出、佣金汇总表和佣金明细 ZIP。
- 是否涉及数据库：否
- 是否需要回滚：是

# 项目记忆

## [2026-06-06 10:25] 修改记录
- 修改内容：修复抖音店铺新模块已注册蓝图但首页与权限系统未接入的问题。权限白名单新增 `douyin_shop_chantelle`、`douyin_shop_mulianman`，用户管理可为普通用户授权；首页新增“香娜露儿（抖音）”和“幕莲蔓（抖音）”两个入口卡片。
- 修改文件：auth/services.py；templates/index.html；PROJECT_MEMORY.md
- 修改原因：新模块路由已存在，但 `MODULE_KEYS` 未包含对应权限 key，首页模板也没有入口，导致本地启动后看不到新模块，普通用户也无法被授予访问权限。
- 影响范围：仅模块权限配置、用户管理模块勾选项和首页入口展示；不影响抖音店铺导入导出业务逻辑、已有模块和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-05 13:54] 修改记录
- 修改内容：修复页头打印 WPS 货物清单按大空格拆分时误把商品数量拆成独立行的问题。后端解析与前端原文展示均新增“纯件数片段并回上一段”规则，支持将 `*1`、`×2`、`1件`、`一瓶` 等仅表示件数的片段合并到前一条商品内容；仍保留大空格拆分多个商品的能力。
- 修改文件：label_print/routes.py；templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：WPS 原始数据中商品名、规格与数量可能在同一行但由多个空格分隔，例如 `50ml  *1`；原规则看到两个以上空格就拆分，导致一条商品被读成两行，并可能把规格数字误当作件数。
- 影响范围：仅页头打印模块 WPS 记录的原文展示与解析分段逻辑；不影响 WPS 在线读取、打印历史、包装推荐和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-05 11:36] 修改记录
- 修改内容：加固微信小店佣金导出的带货账号昵称有效性判断，将订单表昵称 `-` 与空字符串一样视为无效昵称。达人佣金金额匹配、达人佣金回退匹配、带货机构服务费唯一昵称匹配均跳过 `-`，避免导出明细 ZIP 生成 `-.xlsx` 或汇总中出现错误的 `-` 昵称。
- 修改文件：wechat_shop/services.py；PROJECT_MEMORY.md
- 修改原因：5 月佣金老版汇总出现 145 个名称，其中多出的 `-` 来自旧逻辑按订单第一行昵称归属；当前正确口径应为 144 个，需要通过代码防止无效昵称再次参与归属。
- 影响范围：仅微信小店佣金汇总导出和主播/团长佣金明细导出的昵称归属；不影响资金流水、订单原始数据和数据库写入。
- 是否涉及数据库：否（仅修改查询过滤逻辑，不写库）
- 是否需要回滚：是

## [2026-06-05 10:31] 修改记录
- 修改内容：调整微信小店佣金导出中带货机构服务费的昵称归属逻辑。达人佣金继续按资金流水金额优先匹配订单行 `promotion_fee_amount`；带货机构服务费不再回退取订单第一条昵称，而是从订单表 `promotion_fee_channel = '机构服务费'` 且费用非 0 的订单行中取唯一带货账号昵称。无法唯一确定时归入未匹配昵称，避免误归属到达人商品行。
- 修改文件：wechat_shop/services.py；PROJECT_MEMORY.md
- 修改原因：带货机构服务费与达人佣金的核对口径不同，机构服务费更适合按订单机构服务费行的唯一昵称归属；原回退第一条订单昵称在少量订单中可能把机构服务费归到达人昵称。
- 影响范围：仅微信小店佣金导出中的带货机构服务费昵称归属；不影响订单/资金流水导入、原始数据导出、达人佣金金额匹配逻辑和其他模块。
- 是否涉及数据库：否（仅修改查询逻辑，不写库）
- 是否需要回滚：是

## [2026-06-05 00:00] 修改记录
- 修改内容：新增抖音店铺模块——香娜露儿（抖音）和幕莲蔓（抖音）。采用工厂模式：`douyin_shop_common/` 包含共享底层（table_schemas.py、services.py、__init__.py 蓝图工厂），两个店铺各一个薄壳 `__init__.py`（douyin_shop_chantelle、douyin_shop_mulianman）调用工厂生成蓝图。每个店铺建 4 张表：`{prefix}_orders`（订单，CSV，73 列）、`{prefix}_fund_flow`（资金结算，CSV，45 列，跳过第 2 行说明行）、`{prefix}_commission`（佣金订单明细，xlsx，47 列）、`{prefix}_merchant`（招商订单明细，xlsx，31 列，允许空月份不上传）。招商表原始 xlsx 第 21 列和第 30 列均为”订单来源”（平台命名重复），分别存为 order_source_purchase / order_source_traffic。所有表 `CREATE TABLE IF NOT EXISTS` 自动建表，支持按日期范围筛选和导出 xlsx。
- 修改文件：新建 douyin_shop_common/（__init__.py, table_schemas.py, services.py）；新建 douyin_shop_chantelle/__init__.py；新建 douyin_shop_mulianman/__init__.py；新建 templates/douyin_shop.html；修改 app.py（追加两行蓝图注册）
- 修改原因：接入抖音平台（香娜露儿、幕莲蔓两家店铺）数据，格式与微信小店不同，需单独建模
- 影响范围：新增模块，不修改任何已有表；app.py 仅追加两行注册
- 是否涉及数据库：是——新增 8 张表（两个店铺各 4 张），不修改现有表
- 是否需要回滚：是——删除 douyin_shop_common/、douyin_shop_chantelle/、douyin_shop_mulianman/、templates/douyin_shop.html，以及 app.py 中两行注册即可

## [2026-06-04 16:30] 修改记录
- 修改内容：修复佣金导出昵称匹配逻辑。原代码对同一订单的每笔资金流水均取订单表第一条昵称（ORDER BY id ASC LIMIT 1），导致同一订单存在多个带货达人（每人对应不同商品、不同 promotion_fee_amount）时，所有流水笔数均被错误归属到同一人。修复后：优先用资金流水的收支金额（f.amount）与订单表的带货费用（promotion_fee_amount）做精确匹配（误差 < 0.01），找到匹配行取其昵称；无精确匹配时回退到原第一条逻辑。
- 修改文件：wechat_shop/services.py（_query_commission_rows 子查询）
- 修改原因：同一订单含多个达人商品时（如鑫鑫一家在澳洲 31.6 + 黎姐姐在澳洲 34.65），资金流水按商品各出一笔佣金，原代码将两笔均归属到第一个昵称，佣金汇总金额正确但达人归属错误，影响发票开具。
- 影响范围：仅 wechat_shop 佣金导出（汇总 ZIP 和明细 ZIP）；不影响原始数据导入/导出、售后模块及其他流程。
- 是否涉及数据库：否（仅修改查询逻辑，不写库）
- 是否需要回滚：是

## [2026-06-04 15:26] 修改记录
- 修改内容：微信小店模块新增佣金导出区块，支持按资金流水记账日期范围、带货账号昵称关键词或达人/团长别名筛选，导出佣金汇总 ZIP 与主播/团长佣金明细 ZIP；汇总 ZIP 内包含老版汇总 Excel 和发票应开金额导入格式 Excel（仅达人/客户、应开金额两列，默认归属/店铺/期间由发票导入页面补齐）；明细 ZIP 按带货账号昵称拆分 Excel。佣金数据来自资金流水表，并通过关联订单号匹配订单表带货账号昵称；为保持与原 VBA/资金流水汇总口径一致，同一订单存在多条订单行时按订单表第一条带货账号昵称归属；仅统计达人佣金与带货机构服务费，金额正负直接汇总。同步通过代码补建佣金导出查询索引，索引使用 CREATE INDEX IF NOT EXISTS，不修改业务数据。
- 修改文件：wechat_shop/services.py；wechat_shop/routes.py；templates/wechat_shop.html；PROJECT_MEMORY.md
- 修改原因：需要将原 VBA 佣金汇总与拆分明细流程迁移到微信小店 Web 模块中，并额外生成发票应开金额导入格式，便于按日期、昵称或别名直接导出佣金文件。
- 影响范围：仅微信小店佣金导出；不影响原始数据导出、Excel 导入、发票模块和其他业务流程。
- 是否涉及数据库：是（仅读取 wechat_fund_flow、wechat_orders、customer、customer_alias；新增查询索引，不修改业务数据）
- 是否需要回滚：是

## [2026-05-26 14:55] 修改记录
- 修改内容：修复 WPS 今日记录已存在但读取结果为空
  - 确认 `https://kdocs.cn/l/cnaogtuBWmXW` 是 `.dbt` 轻维表，直接访问链接只返回 WPS 前端外壳，不能当作表格内容解析
  - 后端改用金山 `core/execute` 接口：先执行 `http.db.listSheets` 获取字段，再分页执行 `http.db.listRecords` 读取记录
  - 不再固定取第 6 个位置；按字段名优先定位“箱唛-简称-规格*数量，如多件请请换行”作为货物清单列
  - 本地用服务器 Cookie 验证：读取到 1284 行数据，筛出今天 1 条记录，提交时间 `2026/05/26 08:14:05`
- 修改文件：label_print/routes.py；templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：原代码把 WPS 页面 HTML/JS 外壳当成表格行解析，导致接口成功但当天记录数为 0
- 影响范围：页头打印模块的 WPS 读取逻辑；仍只读 WPS，不回写 WPS
- 是否涉及数据库：否
- 是否需要回滚：否

## [2026-05-26 13:45] 修改记录
- 修改内容：页头打印新增 WPS 今日记录处理台
  - 新增 `label_wps_records` 表，首次运行自动建表；只保存从 WPS 读取到的记录，不回写 WPS
  - 按第 2 列"提交时间"只导入当天记录；用整行内容 hash 防止重复导入同一行
  - 页面去掉手工"保存Cookie"按钮，原解析区改为"读取WPS今日记录"横表，显示提交时间、第 6 列内容、解析状态、打印状态和操作
  - 点击记录后显示左右核对区：左侧完整显示第 6 列多行原文，右侧显示可人工修改的解析结果
  - 解析第 6 列时，能匹配货物编号的行识别为编号+数量；无法匹配的行保留为自由文本，打印时原文直接打印
  - `label_print_history` 增加 WPS 记录关联、打印用户、强制重打标记和解析结果快照；打印后更新 WPS 记录的打印次数、最后打印人和最后打印时间
  - 打印历史 Tab 增加操作人和来源列，WPS 已打印记录再次打印会标记为强制重打
- 修改文件：label_print/routes.py；templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：用户需要从 WPS 读取当天记录后逐条人工核对解析并打印，同时保留本系统打印记录防止重复打印
- 影响范围：页头打印模块；新增本地数据库表和打印历史扩展字段；不修改任何 WPS 文件数据
- 是否涉及数据库：是（新增 label_wps_records；扩展 label_print_history）
- 是否需要回滚：是，回滚代码后新增表和字段可保留不影响旧功能

## [2026-05-26 13:15] 修改记录
- 修改内容：修复金山扫码确认后网页仍提示"非法访问（错误码：0x00018）"
  - 重新核对金山官方扫码登录代码：扫码确认返回 `kso_authcode` 时，官方网页不走旧的 `/api/session/exchange/login`，而是走 `/passport/secure/api/grant_token`
  - 后端新增 P-256 ECDSA 密钥生成、公钥 JWK base64url 编码、`kso_authcode` 签名，并用 `kso_authcode + code_verifier + code_sign + public_key + slv=ecdsa_itk` 换取登录 Cookie
  - `api_kdocs_qr_poll` 优先使用 `kso_authcode` 的官方授权流程；只有没有 `kso_authcode` 时才回退旧 `authcode` 流程
  - 同步更新服务器脚本 `scripts/kdocs_login_cookie.py`
  - `requirements.txt` 补充 `cryptography==46.0.7`，保障后续部署有 ECDSA 签名依赖
- 修改文件：label_print/routes.py；scripts/kdocs_login_cookie.py；requirements.txt；PROJECT_MEMORY.md
- 修改原因：前两次只修正二维码创建参数，但扫码确认后的授权换 Cookie 接口仍不匹配金山官方流程
- 影响范围：仅金山 WPS 扫码登录换 Cookie 流程
- 是否涉及数据库：否
- 是否需要回滚：否

## [2026-05-26 12:45] 修改记录
- 修改内容：继续修复金山 WPS 扫码后"非法访问（错误码：0x00018）"
  - 进一步排查金山官方登录页，确认官方 WPS 扫码流程会先生成 PKCE 参数，并把 `code_challenge` 传入 `/api/v3/login_qrcode`
  - 后端新增 `_generate_kdocs_pkce()`，按官方 SDK 算法生成 `code_verifier` 与 `base64url(sha256(verifier))` 格式的 `code_challenge`
  - 页面二维码登录接口现在带 `code_challenge` 创建 loginid，并在扫码会话内保存 `code_verifier`
  - 同步更新 `scripts/kdocs_login_cookie.py` 的二维码创建流程
- 修改文件：label_print/routes.py；scripts/kdocs_login_cookie.py；PROJECT_MEMORY.md
- 修改原因：仅去掉空 `data={}` 后仍报非法访问，说明金山确认登录阶段还校验 PKCE 创建参数
- 影响范围：仅金山 WPS 扫码登录创建 loginid 流程
- 是否涉及数据库：否
- 是否需要回滚：否

## [2026-05-26 12:25] 修改记录
- 修改内容：修复页头打印金山页面扫码后手机端提示"非法访问（错误码：0x00018）"
  - 原因：网页二维码登录接口传了 `data={}`，手机 WPS 可扫码但确认登录页会被金山判为非法访问
  - 修正：生成二维码前先访问 `https://account.wps.cn/wpspersonallogin` 建立同源会话；二维码 URL 改为官方 WPS 扫码页一致的参数，不再传空 JSON `data`
  - 同步修正 `scripts/kdocs_login_cookie.py`，避免命令行二维码也生成非法访问二维码
- 修改文件：label_print/routes.py；scripts/kdocs_login_cookie.py；PROJECT_MEMORY.md
- 修改原因：用户手机扫码后无法确认登录，页面弹出非法访问错误
- 影响范围：仅金山 WPS 扫码登录生成二维码流程
- 是否涉及数据库：否
- 是否需要回滚：否

## [2026-05-26 00:20] 修改记录
- 修改内容：页头打印金山验证改为页面内扫码登录
  - 后端新增 `/label_print/api/kdocs_qr/start`：生成金山 WPS 登录二维码并在 Flask 进程内短暂保存扫码会话
  - 后端新增 `/label_print/api/kdocs_qr/poll`：轮询扫码状态，手机确认后用 authcode 换取登录 Cookie，并保存到 `data/kdocs_cookie.txt`
  - `/label_print/api/kdocs_today_text` 登录/验证码类失败时返回 `need_login=true`，前端据此自动弹出二维码
  - 页头打印界面点击"解析"后，如金山账号密码自动登录触发验证码，页面显示二维码；扫码确认成功后自动继续解析金山当天第 6 列内容
  - 保留手工粘贴 Cookie 功能作为备用
- 修改文件：label_print/routes.py；templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：服务器无浏览器时，不能靠命令行脚本本地打开验证；需要在网页里生成二维码，由手机扫码完成验证后继续解析
- 影响范围：仅 label_print 模块；二维码会话保存在当前 Flask 进程内，适合当前单进程 `app.run` 部署方式
- 是否涉及数据库：否
- 是否需要回滚：否

## [2026-05-25 23:30] 修改记录
- 修改内容：页头打印新增金山文档当天文本解析与服务器端扫码获取 Cookie
  - 打印 Tab 新增"解析txt"文本框与"解析"按钮：读取金山文档 `https://kdocs.cn/l/cnaogtuBWmXW`，按第 2 列"提交时间"筛选当天记录，提取第 6 列内容逐行填入解析文本框
  - 后端新增 `/label_print/api/kdocs_today_text`：支持直接读取金山文档，也支持把表格复制到解析txt后按同一规则解析；返回匹配日期、列名、条数和文本
  - 后端新增金山 Cookie 支持：优先读 `KDOCS_COOKIE`，其次读 `data/kdocs_cookie.txt`，页面可通过 `/label_print/api/kdocs_cookie` 保存登录态
  - 按用户要求保留金山账号密码自动登录尝试：代码内默认账号 `香水梨`、密码 `chenxi98`；自动登录流程为 passkey → RSA 加密密码 → safe_verify → 保存 Cookie；实测金山当前会返回"无效的验证码"
  - 新增服务器脚本 `scripts/kdocs_login_cookie.py`：Ubuntu 24 服务器无浏览器时可运行脚本生成金山登录二维码 URL/PNG，手机 WPS 扫码确认后服务器自动保存 `data/kdocs_cookie.txt`
  - 自动登录遇到验证码时提示运行 `python3 scripts/kdocs_login_cookie.py` 通过扫码获取 Cookie
- 修改文件：label_print/routes.py；templates/label_print.html；scripts/kdocs_login_cookie.py；PROJECT_MEMORY.md
- 修改原因：用户需要页头打印界面从金山 WPS 网络文档自动读取当天提交内容，并且部署在无图形浏览器的 Ubuntu 24 服务器上仍可获取登录 Cookie
- 影响范围：仅 label_print 模块；新增一个服务器维护脚本；`data/kdocs_cookie.txt` 和二维码 PNG 为本地运行文件，不应提交
- 是否涉及数据库：否
- 是否需要回滚：否

## [2026-05-25 22:00] 修改记录
- 修改内容：气泡袋推荐比例参数调整至 1.05，正确推荐 140→中泡、A140→小泡
  - 问题：ratio=0.95 时，140（80×75×71）截面周长 310 > 中泡 BL=300×0.95=285，只有大泡（292≤367.5）才匹配；但实际 140 用中泡足够
  - 根本认知：气泡袋是信封型（flat envelope），允许袋子轻微撑开，ratio 可 >1.0；之前错误套用"袖型"严格约束
  - 修正：ratio=1.05 → 140 截面 310 ≤ 315 ✓ 进中泡；A140 截面 184 ≤ 210 ✓ 进小泡；ratio 值越大推荐越小袋型
  - INIT_SETTINGS 默认值 '0.95' → '1.05'，描述更新说明 >1.0 含义
  - seed 迁移：DB 中值为 '0.9' 或 '0.95'（旧默认未手动修改）的均自动升为 '1.05'
  - 模板 JS fallback 从 0.9 改为 1.05；注释和参数设置面板算法说明同步更新
- 修改文件：label_print/routes.py；templates/label_print.html
- 修改原因：用户确认 140→中泡、A140→小泡 为正确期望；并希望推荐结果向较小袋型靠拢
- 影响范围：仅 label_print 模块气泡袋推荐逻辑；重启服务器后生效
- 是否涉及数据库：是（migration UPDATE bag_girth_ratio 旧值→1.05）
- 是否需要回滚：否

## [2026-05-25 21:30] 修改记录
- 修改内容：修正 bag_girth_ratio 默认值，A140 归入小泡
  - 问题：bag_girth_ratio=0.9 时，A140（57×57×35）截面周长 2×(57+35)=184，小泡 BL=200，184>200×0.9=180，差 4mm 卡在外面，错误推荐中泡
  - 修正：比例改为 0.95，184 ≤ 200×0.95=190 ✓，A140 正确归入小泡；140（80×75×71）仍然只有大泡够用（截面周长 292 > 中泡 285）
  - INIT_SETTINGS 中 bag_girth_ratio 默认值 '0.9' → '0.95'
  - seed_aux_tables 新增迁移语句：若 DB 中 bag_girth_ratio=0.9（旧默认，用户未手动改过），重启时自动升为 0.95
  - 背景：之前用户搞混了 A140 和 140 的尺寸，给出了错误的气泡袋参考案例，此前 fitsBag 修复基于该错误案例
- 修改文件：label_print/routes.py
- 修改原因：用户确认 A140 实际应使用小泡，旧比例参数导致判定过严
- 影响范围：仅 label_print 模块气泡袋推荐逻辑；重启服务器后生效
- 是否涉及数据库：是（migration UPDATE bag_girth_ratio 0.9→0.95，仅限未手动修改过的情况）
- 是否需要回滚：否

## [2026-05-25 21:00] 修改记录
- 修改内容：包装推荐算法增加库存过滤——库存快照 qty≤0 的包材不参与匹配
  - routes.py 新增 `_get_pack_stock()` 函数：查询 `pack_stock_snapshot` 中每个 spec 的最新 qty，返回 `{spec: qty}` 字典
  - `_load_all()` 新增返回值 `pack_stock`，`_render()` 将其作为 `pack_stock` 传入模板
  - 模板新增 JS 变量 `PACK_STOCK_JS`（由服务端 `pack_stock|tojson` 注入）
  - `BOXES`/`BAGS` 构建循环中增加过滤：`if PACK_STOCK_JS.hasOwnProperty(p.n) && PACK_STOCK_JS[p.n]<=0 → return`
  - 无快照记录的包材（如气泡袋）不受影响，仍正常参与匹配
  - 验证：9号箱（qty=0）、12.5号箱（qty=0）不再出现在推荐候选列表中
- 修改文件：label_print/routes.py；templates/label_print.html
- 修改原因：库存为 0 的箱型不应被推荐，避免操作人员按推荐取货发现无货
- 影响范围：仅 label_print 模块前端推荐逻辑；不影响数据库结构
- 是否涉及数据库：否（只读 pack_stock_snapshot，不修改）
- 是否需要回滚：否

## [2026-05-25 20:30] 修改记录
- 修改内容：修复气泡袋推荐算法 fitsBag 物理模型错误
  - 原算法误用袋短边（BW）做周长约束，导致 A140（57×57×35）被错误推荐放入小泡（180×200）
  - 修正物理模型：BW=袋短边（开口，限制插入深度），BL=袋长边（包裹截面，截面周长从此展开）
  - 正确公式：截面周长 `2*(a+b) ≤ BL×ratio` 且 插入深度 `≤ BW`；枚举 3 种放入方向取最优
  - 验证：A140 小泡 BL=200，`2*(57+57)=228 > 200×0.9=180` 不匹配 ✓；中泡 BL=300，`228 ≤ 270` 匹配 ✓
  - 同步更新"参数设置" Tab 中算法说明文本，加入物理模型解释与 A140 验证示例
  - 新参数 bag_girth_ratio 已在代码中定义，若 DB 中尚无此 key，重启服务器后 INSERT OR IGNORE 自动补入
- 修改文件：templates/label_print.html
- 修改原因：气泡袋推荐结果与实际操作不符，物理模型理解有误
- 影响范围：仅 label_print 模块前端推荐逻辑；不影响数据库结构
- 是否涉及数据库：否
- 是否需要回滚：否

## [2026-05-25 19:00] 修改记录
- 修改内容：新增包装推荐功能（前端算法 + 预设规则 + 参数设置）
  - 气泡袋尺寸全部改为 mm：大泡 250×350、中泡 200×300、小泡 180×200（原为 cm 录入错误）
  - 新增 label_pack_presets 表：存已知货物组合（combo_key 格式 "113B×1+140×2"）→ 预设箱型 + 气泡袋 + 备注；CRUD 路由完整
  - 新增 label_pack_settings 表：存 6 个可调参数（buffer_mm / fill_rate_single / fill_rate_multi / irregular_factor / complex_threshold / bag_girth_ratio），INSERT OR IGNORE 保证新参数自动补入且不覆盖用户修改
  - 新增"预设规则" Tab：左侧表单（组合编号 + 箱型 select + 气泡袋 select + 备注），右侧横表，点击行填入表单
  - 新增"参数设置" Tab：参数表单 + 内嵌算法说明文本（防止遗忘）
  - 打印 Tab 汇总区下方新增推荐显示区（rec-display），实时随输入更新
  - 前端 JS 推荐算法：① 查预设表 → ② 单品6朝向精确计算 → ③ 多品体积估算+最大单件约束 → ④ 超阈值不预览；气泡袋按截面周长约束（(a+b) ≤ 袋宽×比例）枚举方向选最小
  - 推荐区显示组合编号小字，点击复制，方便添加预设
  - doPrint() 在打印页底部追加一行推荐包装（多页仅末尾出现一次）
- 修改文件：label_print/routes.py；templates/label_print.html
- 修改原因：根据已有货物尺寸和包材尺寸数据，为打印操作提供包装推荐参考
- 影响范围：仅 label_print 模块；新增 2 张表（label_pack_presets、label_pack_settings）在 data/main.db
- 是否涉及数据库：是（新增 label_pack_presets、label_pack_settings；气泡袋尺寸数据通过 INSERT OR REPLACE 自动修正）
- 是否需要回滚：否

## [2026-05-25 17:50] 修改记录
- 修改内容：包材尺寸规范化 + 补充初始数据
  - INIT_PACKING_SIZES 改用 pack_item.name 规范名称（11号→11，半高11号→11.5，以此类推），剔掉 pack_item 中不存在的型号（1/2/3/4号及对应半高版本）
  - 新增 3 条初始数据：大泡（25×35）、中泡（20×30）、小泡（18×20）
  - seeding 逻辑从 INSERT OR IGNORE 改为 INSERT OR REPLACE，保证重启后旧名称数据自动被新规范名称覆盖同步
  - 模板"包材尺寸" Tab 的表单输入改为下拉框（复用 pack_names，来源 pack_item.name），与"包材重量"一致
  - 横表点击行填入表单也改为操作 select 控件
- 修改文件：label_print/routes.py；templates/label_print.html
- 修改原因：包材名称需与 pack_item.name 保持一致（半高用 .5 表示），且需支持大泡/中泡/小泡的尺寸记录
- 影响范围：仅 label_print 模块 label_packing_sizes 表及对应页面；不影响其他模块
- 是否涉及数据库：是（label_packing_sizes 数据更新，重启后 INSERT OR REPLACE 自动同步）
- 是否需要回滚：否

## [2026-05-25 17:30] 修改记录
- 修改内容：新增"包材尺寸"辅助表与管理页面
  - 新增 label_packing_sizes 表：pack_name（TEXT UNIQUE）、size（TEXT，存"长×宽×高"文本）、updated_at
  - 写入 22 条初始数据（12号～1号 + 半高11号～半高2号，尺寸数据来自截图）；seeding 逻辑与其他辅助表一致（表为空时才插入）
  - _load_all() 增加 packing_sizes 返回值，_render() 透传给模板
  - 新增路由：GET /packing_sizes（页面）、POST /packing_sizes/upsert、POST /packing_sizes/<id>/delete
  - 模板 Tab 栏在"包材重量"和"打印历史"之间插入"包材尺寸"按钮（id=tabBtn-packing_sizes）
  - 模板 Panel：左侧表单（包材名称文本框 + 尺寸文本框 + 提交），右侧横表（点击行填入表单，同名→更新，新名→新增）
- 修改文件：label_print/routes.py；templates/label_print.html
- 修改原因：用户需要按包材型号（11号、半高11号等）维护外箱尺寸参考数据，为后续体积估算提供数据基础
- 影响范围：仅 label_print 模块；新增 1 张表（label_packing_sizes）在 data/main.db；不影响其他模块
- 是否涉及数据库：是（新增 label_packing_sizes 表，CREATE IF NOT EXISTS，首次启动自动建表并插入初始数据）
- 是否需要回滚：否（新增表，不修改已有表结构）

## [2026-05-25 16:00] 修改记录
- 修改内容：页头打印模块 Round 4 - 功能完善
  - 修复模糊查询 Bug：oninput 阶段只做精确匹配（不自动补全、不跳转），onblur 阶段才执行三级模糊查询（精确→唯一 endsWith→唯一 includes）并自动补全完整编号，解决输入"1"尚未完成时直接跳到"114"的问题
  - 新增 label_packing_weights 表：包材名称来源 pack_item.name（前端下拉框受限），另有重量列；初始无数据，等待手工录入；CRUD 路由与其他辅助表一致
  - 新增 label_print_history 表：每次执行打印时自动 AJAX 保存 total_tickets、total_qty、items_json、printed_at；新增"打印历史"Tab 展示最近 100 条记录，支持逐条删除
  - 前端新增"包材重量"和"打印历史"两个 Tab，共 6 个 Tab
  - _load_all() 增加 pack_names 参数（从 pack_item 查取）；_render() 透传 pack_names 给模板
  - 新增 API /api/save_print（POST），接收 JSON 写入 label_print_history
- 修改文件：label_print/routes.py；templates/label_print.html
- 修改原因：用户反馈模糊查询过早触发影响输入体验；需要包材重量和打印历史两张管理表
- 影响范围：仅 label_print 模块；新增 2 张表（label_packing_weights、label_print_history）；pack_item 表只读查询，不修改
- 是否涉及数据库：是（新增 label_packing_weights、label_print_history 两张表；表在 data/main.db 中按需 CREATE IF NOT EXISTS 创建）
- 是否需要回滚：否（新增表，不影响已有表结构）

## [2026-05-25 14:30] 修改记录
- 修改内容：新增页头打印模块（label_print）完整实现
  - 新建 label_print/ 蓝图（__init__.py + routes.py），注册到 app.py url_prefix=/label_print
  - 新增 auth/services.py MODULE_KEYS/MODULE_LABELS 加入 label_print / 页头打印
  - 新增 templates/label_print.html，含 4 个管理 Tab（产品管理、货物重量、尺寸管理）及打印 Tab
  - 新增 templates/index.html 首页卡片"页头打印"（权限守卫 can_module）
  - 新增 label_products 表：code/short_name/product_name/spec/box_spec，初始数据从 temp/打印页头.xlsx Sheet2 导入
  - 新增 label_weights 表：22 条初始货物重量数据
  - 新增 label_sizes 表：22 条初始尺寸数据（长/宽/高/is_irregular）；编号 184 标记 is_irregular=1（两端高度不同）
  - 打印功能：全局总票数输入 + 动态多行（货物编号/每票件数/箱数/总件数）；箱数同时显示"N箱+M个"和"N+1箱-K个"两种形式；打印尺寸 76mm×130mm，自动分页
  - 产品管理：横表展示现有数据，点击行填入表单，同编号提交→更新，新编号→新增
  - 货物重量 / 尺寸管理：同上 upsert 交互
  - 修复：index() 路由未传 products 导致产品管理 Tab 数据为空；改为通过统一 _render() 传全量数据
- 修改文件：新增 label_print/__init__.py；新增 label_print/routes.py；新增 templates/label_print.html；修改 auth/services.py；修改 app.py；修改 templates/index.html
- 修改原因：用户需要内部打印页头标签的管理工具，替代原手工 Excel 操作
- 影响范围：新增模块，不影响其他模块；新增 3 张表（label_products、label_weights、label_sizes）在 data/main.db
- 是否涉及数据库：是（新增 label_products、label_weights、label_sizes 三张表）
- 是否需要回滚：否（新增模块与表，不改动已有表结构）

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
## [2026-05-03 09:25] 修改记录
- 修改内容：完成当前 Flask 系统在纽约服务器的首次部署，上传并恢复主数据库 `data/main.db`、应用密钥 `data/.app_secret_key`、发票 PDF 目录 `data/invoice_pdfs` 与待处理目录 `data/invoice_pdfs_pending`；在服务器创建 Python 虚拟环境并安装依赖；启动 Flask 服务监听 `0.0.0.0:5001`；放行服务器防火墙 `5001/tcp`；新增纽约服务器手工运维文档 `NEWYORK_SERVER_RUNBOOK.md`，记录地址、密码、部署与启停命令。
- 修改文件：PROJECT_MEMORY.md，NEWYORK_SERVER_RUNBOOK.md
- 修改原因：需要将当前系统完整迁移部署到纽约服务器，并保留后续可手工复用的部署/运维说明。
- 影响范围：纽约服务器 `64.176.214.252` 的 `/root/my-flask-project` 项目目录、Python 虚拟环境、Flask 5001 端口服务、防火墙放行规则，以及仓库内运维文档。
- 是否涉及数据库：是
- 是否需要回滚：是
## [2026-05-03 09:34] 修改记录
- 修改内容：将纽约服务器 `64.176.214.252` 的 `root` 登录密码从初始复杂密码调整为便于手工输入的新密码；新密码仅记录在本地运维文档中，不提交到 Git 仓库。
- 修改文件：PROJECT_MEMORY.md，NEWYORK_SERVER_RUNBOOK.md
- 修改原因：原始密码包含特殊字符，不便于日常手工 SSH 登录与运维操作。
- 影响范围：纽约服务器 `root` 账户登录凭据，以及仓库内纽约服务器运维文档。
- 是否涉及数据库：否
- 是否需要回滚：是
## [2026-05-03 10:31] 修改记录
- 修改内容：修复微信小店多文件 Excel 上传兼容性与上传上限配置；`requirements.txt` 增加 `xlrd==2.0.1` 以支持 `.xls` 文件读取；`app.py` 增加 `MAX_CONTENT_LENGTH=512MB`，让直连 `5001` 的 Flask 上传入口也有明确请求体上限；同步补充 `NEWYORK_SERVER_RUNBOOK.md` 中纽约服务器上传限制检查说明。
- 修改文件：app.py，requirements.txt，NEWYORK_SERVER_RUNBOOK.md，PROJECT_MEMORY.md
- 修改原因：前端和后端允许 `.xls/.xlsx` 多文件上传，但服务器缺少 `.xls` 读取依赖；纽约服务器常用 `:5001` 直连 Flask，需在应用层明确上传体积上限。
- 影响范围：微信小店订单/资金流水/售后 Excel 导入的 `.xls` 兼容性；纽约服务器 Flask 上传请求体上限；运维文档。
- 是否涉及数据库：否
- 是否需要回滚：是
## [2026-05-03 10:40] 修改记录
- 修改内容：复核微信小店多文件上传与下载报错链路，修复“数据已写入但收尾步骤失败导致前端误报导入失败”的隐患；上传日志写入改为诊断性 best-effort，不再影响导入结果；数据状态刷新失败时返回成功并附加提示；导入完成后刷新状态表 HTML 失败时不再让请求 500；导出失败时前端改用统一响应解析，避免非 JSON 错误页造成模糊解析报错。
- 修改文件：common/upload_staging.py，wechat_shop/routes.py，wechat_shop/services.py，templates/wechat_shop.html，PROJECT_MEMORY.md
- 修改原因：此前多文件上传曾出现前端报错但数据实际导入成功，说明主流程成功后的日志、状态刷新或页面刷新收尾异常可能被误判为导入失败；下载失败也需要保留更可读的错误提示。
- 影响范围：微信小店订单/资金流水/售后 Excel 导入结果判定与提示；微信小店原始数据导出失败提示；不改变数据写入规则和表头一致性校验规则。
- 是否涉及数据库：否
- 是否需要回滚：是
## [2026-05-03 10:42] 修改记录
- 修改内容：修正纽约服务器手工运维文档中的 Flask 进程查找/停止命令，改用 `ps -eo pid=,comm=,args=` 并限定进程名为 Python，避免远程执行重启脚本时误匹配当前 shell 命令导致服务被停止后未重新拉起。
- 修改文件：NEWYORK_SERVER_RUNBOOK.md，PROJECT_MEMORY.md
- 修改原因：复核部署时发现原重启命令的进程匹配范围偏宽，远程自动执行场景下可能误杀当前重启命令所在 shell。
- 影响范围：纽约服务器手工停止/重启命令文档；不影响业务代码和数据库。
- 是否涉及数据库：否
- 是否需要回滚：是
## [2026-05-03 10:46] 修改记录
- 修改内容：调整微信小店多文件 Excel 导入预检规则，订单/资金流水/售后三类导入在任一文件读取失败、缺少必需字段或列结构不一致时，整批返回“预检未通过，未写入数据库”，不再导入其中部分正常文件；表头不一致文件也不再加入待写入 DataFrame。
- 修改文件：wechat_shop/services.py，PROJECT_MEMORY.md
- 修改原因：避免多文件上传时部分文件成功写库、部分文件报错造成“数据看似已导入但页面提示失败”的困惑；表头不一致应在写库前作为整批预检失败处理。
- 影响范围：微信小店订单、资金流水、售后 Excel 多文件导入的异常处理；正常同结构多文件导入不受影响。
- 是否涉及数据库：否
- 是否需要回滚：是
## [2026-05-03 10:55] 修改记录
- 修改内容：复核微信小店原始数据 Excel 下载链路，修复导出请求未携带 AJAX/JSON 头导致登录失效时可能把登录页 HTML 当作 Excel blob 下载的问题；前端导出请求增加 `Accept: application/json` 与 `X-Requested-With: XMLHttpRequest`，并在下载前校验响应必须为 Excel 附件。
- 修改文件：templates/wechat_shop.html，PROJECT_MEMORY.md
- 修改原因：此前下载表格文件曾出现报错但未记录具体内容；复核发现登录过期/权限失效场景会返回 HTML 页面而非 Excel，旧前端可能误判为下载成功或给出模糊错误。
- 影响范围：微信小店原始数据 Excel 导出失败提示；正常登录态下 Excel 下载不受影响。
- 是否涉及数据库：否
- 是否需要回滚：是
## [2026-05-15 21:15] 修改记录
- 修改内容：发票匹配关系升级为中间表 `invoice_expected_match`，字段为 `invoice_id`、`expected_amount_id`、`matched_amount`、`created_at`；历史 227 张已匹配发票已回填中间表，1 张未匹配发票保持空匹配；发票复核入库、发票列表单张匹配页、列表“设为可用”快捷操作均改为写入中间表；发票列表与批量下载命名优先从中间表关联的 `expected_amount.platform/period` 读取账期；应开 vs 已开核对页的已开归属平台优先使用中间表匹配账单平台。
- 修改文件：invoicing/routes.py；templates/invoicing_invoice_match.html；templates/invoicing_invoices_review.html；templates/invoicing_invoices.html；data/main.db；PROJECT_MEMORY.md
- 修改原因：修复历史发票下载时按达人/团长动态推断最新账期，导致旧发票被命名成新账期的问题；保存确定的“发票 -> 应开账单”关系，避免新增账期影响历史发票。
- 影响范围：发票复核、发票匹配、发票列表展示、批量下载 ZIP 命名、应开 vs 已开核对页已开归属平台；达人/团长昵称管理仍按 `expected_amount` 汇总，不依赖中间表。
- 是否涉及数据库：是（已备份 `data/main_backup_before_invoice_expected_match_20260515_210147.db`）
- 是否需要回滚：是
## [2026-05-15 21:24] 修改记录
- 修改内容：复核发票 `26372000001596608446`，确认其通过 `invoice_expected_match` 绑定 `expected_amount_id=76`、对应 `香娜露儿 / 25年34季度`，但发票本身确认为不可用；已将误设的 `is_usable=1` 回滚为 `is_usable=0`。
- 修改文件：data/main.db；PROJECT_MEMORY.md
- 修改原因：人工复核后确认该发票不应计入已开金额，核对页显示 1949 已开为 0 属于当前可用口径下的正确结果。
- 影响范围：仅该发票是否计入应开 vs 已开核对与相关汇总；不影响中间表匹配关系。
- 是否涉及数据库：是
- 是否需要回滚：否
## [2026-05-15 21:34] 修改记录
- 修改内容：发票复核页与单张发票匹配页的候选下拉新增”已开”金额展示，已开按当前候选账期对应的 `invoice_expected_match` 已匹配金额汇总；”匹配后”改为 `应开 - 已开 - 当前发票金额`；候选排序改为按 `abs(匹配后)` 从小到大，匹配后为 0 的候选优先显示。修改已有发票时，候选已开金额会排除当前发票自身，避免重复扣减。
- 修改文件：invoicing/routes.py；templates/invoicing_invoice_match.html；templates/invoicing_invoices_review.html；PROJECT_MEMORY.md
- 修改原因：匹配时需要直接看到该账期已经被发票占用的金额，并优先展示最接近完全匹配的候选。
- 影响范围：仅发票复核/匹配候选展示与排序；不改变已保存的发票匹配关系、核对页汇总口径和达人/团长昵称管理汇总。
- 是否涉及数据库：否
- 是否需要回滚：否

## [2026-05-25 14:30] 修改记录
- 修改内容：新增页头打印模块（label_print）
  - 新建 label_products 表（字段：code/short_name/product_name/spec/box_spec），首次访问自动从 temp/打印页头.xlsx Sheet2 导入 25 条产品数据
  - 打印页面：动态添加货物行（货物编号 / 每票件数 / 总票数），输入编号后自动填充仓库简称，自动计算箱数（整箱显示”N箱”，不足整箱显示”N箱-M个”），实时汇总总票数/总数量
  - 打印格式同操作入库（76mm×130mm 快递单贴纸），每行显示”简称 * 件数 箱数”，最后显示一次总票数和总数量，超出自动分页
  - 产品管理页：支持新增/行内编辑/删除产品，维护 label_products 表
  - 接入授权体系（module_key=label_print），首页加「页头打印」卡片
- 修改文件：
  - 新增：label_print/__init__.py、label_print/routes.py、templates/label_print.html
  - 修改：auth/services.py、app.py、templates/index.html、PROJECT_MEMORY.md
- 修改原因：用户需要 Web 化替代手工 Excel 打印页头，并加入箱数自动计算辅助配货
- 影响范围：新增独立模块；现有模块路由与逻辑不动；普通用户默认无 label_print 权限，需管理员授权
- 是否涉及数据库：是（新增 label_products 表，首次访问自动建表并从 xlsx 导入）
- 是否需要回滚：否（git revert 相关文件 + 删除 label_print/ 目录即可）

## [2026-05-27 12:17] 修改记录
- 修改内容：发票列表新增“导出选中 Excel”按钮，支持将选中发票的发票号、日期、类型、税率、金额、销售方、购买方导出为 Excel；导出顺序按当前页面排序后的选中顺序；发票号码按文本格式写入，避免 Excel 科学计数法显示；生成文件保存到当前用户桌面并作为浏览器下载返回。
- 修改文件：invoicing/routes.py；templates/invoicing_invoices.html；PROJECT_MEMORY.md
- 修改原因：需要从发票列表快速导出选中发票的关键字段，便于外部核对和整理。
- 影响范围：仅发票列表页面与新增 Excel 导出接口；不影响发票 PDF 下载、上传、匹配、删除流程。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-27 15:39] 修改记录
- 修改内容：页头打印包装推荐中新增异形货物堆叠等效尺寸计算；异形货物多件推荐箱型时，不再直接按完整外接尺寸逐件计数，而是按长边、宽边不变，高度随件数小幅叠加的组合尺寸参与现有箱型匹配。
- 修改文件：templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：184 为牙膏形异形货物，一头高一头低，实际多件摆放时可错位叠放；原逻辑按完整长方体件数计算，容易把 184×1、184×2、184×3 推荐到偏大的箱型。
- 影响范围：仅页头打印模块包装推荐中的异形货物箱型估算；不修改尺寸管理原始数据、不影响气泡袋推荐、打印、WPS 读取和其他普通货物的通用装箱逻辑。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-27 16:08] 修改记录
- 修改内容：页头打印包装推荐新增仓库实际样本校准层，并新增 `PACKING_RECOMMENDATION_RULES.md` 记录当前装箱推荐规则；推荐箱型优先匹配已知实际样本，未命中时继续走通用算法，并在误差较小时倾向 `11`、`10` 等仓库常用整数箱型。
- 修改文件：templates/label_print.html；PACKING_RECOMMENDATION_RULES.md；PROJECT_MEMORY.md
- 修改原因：当前通用装箱算法与仓库实际装箱习惯存在偏差，需要用实际样本校准，并记录规则方便后续继续迭代。
- 影响范围：仅页头打印模块推荐箱型；不影响气泡袋推荐、尺寸管理原始数据、打印、WPS 读取和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-27 16:54] 修改记录
- 修改内容：页头打印 WPS 今日记录读取扩展为双来源，新增读取 `https://kdocs.cn/l/cqUIdRBp3yCl`；两个来源均按提交时间筛选当天记录，并继续按来源+整行哈希防重；WPS 记录列表新增来源列；第 6 列解析新增产品简称关键词匹配，并支持中文数字数量如“一、两、十”。
- 修改文件：label_print/routes.py；templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：需要同时读取第二个 WPS 表的今日提交记录，且新表第 6 列内容不规范，第一版先通过产品管理中的简称关键词辅助解析，如临时产品 `BSPF / 防晒` 可从“防晒一瓶”等文本匹配。
- 影响范围：仅页头打印模块 WPS 今日记录读取、列表展示和解析逻辑；不回写 WPS，不影响打印、包材推荐和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-28 15:10] 修改记录
- 修改内容：页头打印实际打印模板整体下移 8mm；货物简称和每票件数字体放大 1.5 倍；共计和总数量保持 14px 并改为单行显示；打印底部新增不加粗的预估重量显示，并在缺少重量数据时提示缺少项；预估重量与推荐包装之间的行距减半。
- 修改文件：templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：需要调整快递单贴纸上的打印位置和字号，并让纸质页头同步显示当前推荐包装口径下的预估重量。
- 影响范围：仅页头打印模块的打印窗口样式与打印内容；不影响页面录入、WPS 读取、包材推荐算法和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-29 10:15] 修改记录
- 修改内容：页头打印 WPS 原文和列表内容按大空格/制表符拆为一行一个商品显示；打印底部共计、总数量、预估重量改为 flex 对齐；WPS 第 6 列解析支持一行多个产品，新增产品名、简称、简称+规格的模糊匹配，数量解析优先识别 `*1` 等明确件数并避免把 `100ml/250ml` 当数量；模糊匹配时增加规格冲突保护，未匹配内容保留为自由文本用于打印。
- 修改文件：label_print/routes.py；templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：实际 WPS 数据排版依赖空格对齐，导入网页后需要保持整齐；第 6 列输入不规范，部分产品需通过产品管理中的名称/简称模糊定位，未建档内容也需要能正常打印。
- 影响范围：仅页头打印模块 WPS 记录展示、解析和打印底部样式；不影响 WPS 读取来源、包材推荐算法和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-29 10:32] 修改记录
- 修改内容：页头打印 WPS 解析中自由文本也提取明确件数（如 `100ml*1` 的数量为 1），打印和总数量统计会随总票数同步变化；自由文本打印时显示可识别件数；继续保留规格冲突保护，避免 `绵羊油/250ml` 与后续可能新增的 `日升绵羊油/100ml` 混淆。
- 修改文件：label_print/routes.py；templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：未匹配产品管理的文本仍可能包含明确件数，需纳入总数量；同时需要避免短简称覆盖长简称或不同规格产品。
- 影响范围：仅页头打印模块 WPS 解析、打印内容和总数量统计；不影响 WPS 读取来源、包材推荐算法和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-28 14:44] 修改记录
- 修改内容：发票核对应开金额页面新增查询区域，支持通用查询条件匹配店铺/平台、期间、归属、起止日期，客户框支持匹配客户简称和客户别名；页面新增当前查询结果的应开金额合计显示；导入后列表刷新沿用同一套查询与合计逻辑。
- 修改文件：invoicing/routes.py；templates/invoicing_expected_amounts.html；PROJECT_MEMORY.md
- 修改原因：用户需要在应开金额记录中按输入条件快速筛选，并查看符合查询记录的应开金额合计。
- 影响范围：仅影响发票核对模块的应开金额列表查询、记录数显示和合计展示；不影响 Excel 导入、发票上传、发票匹配和核对汇总逻辑。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-28 14:59] 修改记录
- 修改内容：发票核对应开金额页面的通用查询支持多个条件，按空格、逗号、顿号、分号拆分关键词；多个关键词之间为同时满足，每个关键词可匹配店铺/平台、期间、归属、起止日期任一字段；同步更新查询框占位提示。
- 修改文件：invoicing/routes.py；templates/invoicing_expected_amounts.html；PROJECT_MEMORY.md
- 修改原因：用户希望通用查询框可以一次输入多个查询条件进一步缩小应开金额记录范围。
- 影响范围：仅影响应开金额列表的通用查询条件解析和页面提示；客户查询、导入、发票匹配和核对汇总逻辑不变。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-30 10:38] 修改记录
- 修改内容：页头打印通用装箱容量计算调整为同品多件按实物尺寸堆叠，不再把 `buffer_mm` 重复加到每一件货物上；整数箱偏好体积容忍系数从 `1.35` 调整为 `1.4`；同步补充装箱规则文档。验证样本规则保持命中，`A160×7` 与 `A161×7` 推荐为 `10` 号箱。
- 修改文件：templates/label_print.html；PACKING_RECOMMENDATION_RULES.md；PROJECT_MEMORY.md
- 修改原因：当前逐件叠加 buffer 导致多件小件/薄件容量被过度放大，`A160×7`、`A161×7` 无法按实际仓库习惯推荐 10 号箱。
- 影响范围：仅页头打印模块未命中样本规则时的通用箱型推荐；已记录的仓库样本规则仍优先，不影响 WPS 读取、打印模板和数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-05-30 11:16] 修改记录
- 修改内容：页头打印通用装箱算法新增同商品多件箱型下限保护：未命中整组仓库样本时，同一商品多件推荐箱型不得小于该商品 `×1` 的已知样本、预设或计算箱型；若因此被拉回单件下限，不再继续套用整数箱偏好；同步补充装箱规则文档。
- 修改文件：templates/label_print.html；PACKING_RECOMMENDATION_RULES.md；PROJECT_MEMORY.md
- 修改原因：实测 `A160×1` 命中仓库样本为 `10.5`，但 `A160×2`、`A160×3` 走通用容量算法时反而推荐更小的 `11.5`，不符合件数增加的装箱直觉。
- 影响范围：仅页头打印模块未命中整组样本时的同商品多件箱型推荐；已记录仓库样本、预设规则、WPS 读取、打印模板和数据库结构不受影响。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-07 10:21] 修改记录
- 修改内容：抖音店铺（香娜露儿/幕莲蔻）新增佣金导出功能。达人佣金来自 fund_flow.influencer_commission 按 influencer_name 分组；团长佣金来自 fund_flow.merchant_recruitment_fee 按 merchant.issuing_institution 分组（JOIN 招商表）。汇总 ZIP 包含佣金汇总表、应开金额导入格式和可能的未匹配招商订单警告文件；明细 ZIP 包含按达人/团长拆分的明细文件。金额统计先正负相加取净值，再取绝对值。order_no 前导单引号通过 LTRIM 清洗后 JOIN。
- 修改文件：douyin_shop_common/services.py；douyin_shop_common/__init__.py；templates/douyin_shop.html
- 修改原因：对齐微信小店佣金导出功能，适配抖音平台的资金结算表与招商订单明细表数据结构。
- 影响范围：仅抖音两个店铺模块；不影响微信小店、发票及其他模块。
- 是否涉及数据库：否（只读）
- 是否需要回滚：是

## [2026-06-07 10:45] 修改记录
- 修改内容：补充抖音店铺招商数据后复核佣金导出，发现团长佣金 SQL JOIN 在全期间真实数据上执行过慢；将团长汇总、未匹配招商订单和团长明细的匹配逻辑改为先读取招商表 order_id -> issuing_institution 映射，再在 Python 内按清洗后的资金表 order_no 归属。保留原有导出结构、金额净值后取绝对值规则和未匹配警告文件规则。
- 修改文件：douyin_shop_common/services.py
- 修改原因：真实招商数据导入后，全期间汇总导出使用 LTRIM JOIN 超时；需要在不修改数据库结构、不新增索引的前提下完成团长佣金检查和导出。
- 影响范围：仅抖音店铺佣金导出的团长佣金匹配路径；达人佣金、原始数据导入导出、微信小店和发票模块不受影响。
- 是否涉及数据库：否（只读）
- 是否需要回滚：是

## [2026-06-07 11:22] 修改记录
- 修改内容：修正抖音店铺佣金汇总金额口径，达人汇总、团长汇总和应开金额导入不再对每个分组佣金净额取绝对值，改为保留资金结算表中的正负净额；正数表示退款导致的支出退回，负数表示佣金支出。导出排序仍按金额绝对值大小排序，便于查看大额记录。
- 修改文件：douyin_shop_common/services.py
- 修改原因：5 月资金结算表 AH 列达人佣金存在正负数，原逻辑按达人/团长分组后取绝对值会把退款退回金额放大为支出，导致资金流水列净和与佣金汇总合计不一致。
- 影响范围：仅抖音店铺佣金汇总 ZIP 和应开金额导入文件的金额符号口径；佣金明细仍保留原始资金行金额，原始数据导入导出、微信小店和发票模块不受影响。
- 是否涉及数据库：否（只读）
- 是否需要回滚：是

## [2026-06-07 13:47] 修改记录
- 修改内容：从西班牙马德里服务器 `208.85.17.83` 只读备份 `/root/my-flask-project/data` 完整目录到本地 `backups/my-flask-project_data_madrid_backup_20260607_134335.tar.gz`。备份包大小 270.55 MB，包含 382 个条目、306 个 PDF、55 个 JSON；抽取 `data/main.db` 后执行 `PRAGMA integrity_check` 返回 `ok`。
- 修改文件：backups/my-flask-project_data_madrid_backup_20260607_134335.tar.gz；PROJECT_MEMORY.md
- 修改原因：需要将西班牙服务器端数据完整拷贝到本地留存备份。
- 影响范围：仅新增本地备份压缩包与项目记录；不覆盖本地 `data/`，不修改远端业务数据。远端传输用临时压缩包已在校验完成后删除。
- 是否涉及数据库：是（备份 SQLite 数据库文件，仅只读校验，不写库）
- 是否需要回滚：否（如不再需要，删除本地备份压缩包即可）

## [2026-06-07 14:08] 修改记录
- 修改内容：西班牙马德里服务器 `208.85.17.83` 从 GitHub `origin/main` 拉取最新代码并重启 Flask 服务。服务器从 `833e814` fast-forward 到 `7589454`，新增抖音店铺模块相关代码；使用项目虚拟环境 `.venv/bin/python` 启动新进程 `221763`，公网与本机登录页均返回 HTTP 200。
- 修改文件：服务器 `/root/my-flask-project`；PROJECT_MEMORY.md
- 修改原因：需要让西班牙服务器运行 GitHub 最新代码。
- 影响范围：西班牙服务器线上 Flask 应用代码与运行进程；未覆盖服务器 `data/`，未修改业务数据。更新前已在服务器 `/root` 生成代码备份 `my-flask-project_code_backup_before_github_pull_20260607_1404.tar.gz` 和数据备份 `my-flask-project_data_backup_before_github_pull_20260607_1404.tar.gz`。
- 是否涉及数据库：否（仅备份数据目录，不写库）
- 是否需要回滚：是（可用服务器备份包恢复代码/数据，或 git 回退到旧提交后重启服务）

## [2026-06-07 15:34] 修改记录
- 修改内容：将本地佣金导出代码合入并推送到 GitHub `main`，提交从 `7589454` 更新到 `6076310`；西班牙马德里服务器 `208.85.17.83` 已拉取该提交并用 `.venv/bin/python` 重启 Flask 服务，确认服务器模板包含“佣金导出”区块和 `export_commission_summary`、`export_commission_details` 接口。同步比对香娜露儿招商订单明细：本地 `dy_chantelle_merchant` 为 26408 条，服务器为 26087 条；当前导入目录 `D:\BaiduSyncdisk\MyWork\佣金计算\香娜露儿` 下 5 个招商 Excel 合计 26087 个唯一订单，和服务器完全一致。本地多出的 321 条均为 2026-05、状态为“订单结算”，且不在当前 5 个招商 Excel 中。差异明细输出到 `backups/chantelle_merchant_diff_local_server_import.csv`，摘要输出到 `backups/chantelle_merchant_diff_summary.txt`。
- 修改文件：PROJECT_MEMORY.md；服务器 `/root/my-flask-project`；本地比对输出 `backups/chantelle_merchant_diff_local_server_import.csv`、`backups/chantelle_merchant_diff_summary.txt`
- 修改原因：需要把本地最新佣金导出代码发布到 GitHub 并更新西班牙服务器，同时排查香娜露儿招商订单明细本地与服务器差异来源。
- 影响范围：GitHub `main`、西班牙服务器代码和运行进程；数据库仅只读比对，不写入、不覆盖。比对结论显示服务器招商表与当前导入文件一致，本地库额外 321 条疑似来自旧版或其他招商文件。
- 是否涉及数据库：是（只读查询本地与服务器 SQLite 数据库，不写库）
- 是否需要回滚：是（代码可回退到 `7589454` 并重启；数据库未修改无需回滚）

## [2026-06-09 21:22] 修改记录
- 修改内容：快递费模块（Tab3 快递账单）核对逻辑大修 + 重量预估算法后端单一源化。具体：
  1. 发货内容解析 OPT_04：移植 VBA `SPX_PC_ParseShipText`，新增 `ship_content_key`（排序聚合Key，如 `113B*2;140*1`），修复 `[n]` 拍下数乘数、组合段(含「组合」)解析；
  2. 重量核查 OPT_05 重做：废弃固定 0.03/0.22 包材常量与百分比范围估算，改为「按页头打印逻辑实际匹配箱型+气泡袋，货物+包装预估整件重量」，结算重量 ≤ 预估×(1+允差%) 记「是」，算不出重量则假设对方正确；
  3. 真·重量异常过滤（对齐 VBA `OPT_ShouldExportWeightErr`）：仅「否」且「实收 > 起步费」才计为重量异常（只收起步费的不与快递较真）。202605 实测重量异常 9081→5；
  4. 价格核对 OPT_03 增「最低收费忽略」(实收≈起步费)；重量异常行不再误判为价格异常；
  5. 计费规则新增可配置 `weight_tolerance_pct`（重量允差%，默认20%），计费标准页可编辑；
  6. 底单导入修复：发货时间非日期（退货/占号「已占用单号但未发货」「已回收面单」）不再整行丢弃，有单号/订单号即保留（发货时间留空），空白异常 13→1（需重新导入底单生效）；
  7. 修正文件下载改 openpyxl：修正行黄色填充 + 「修正说明」列 + 文件名含修正后总金额 + 仅导出当前未核查批次文件；
  8. 箱型推荐库存过滤 bug 修复：停用包材（库存=0，如箱9）不再被推荐，与页头打印一致；
  9. 横表展示列新增 发货内容排序Key/预估重量/允差上限，结算重量与预估并排。
- 修改文件：
  - 新增 `label_print/pack_recommend.py`（包装推荐+预估重量唯一算法源，PackRecommender）
  - `label_print/routes.py`（新增 `POST /label_print/api/recommend` 接口）
  - `templates/label_print.html`（删除约340行重复JS算法，改为防抖200ms请求后端；打印预估重量改用后端结果）
  - `courier_fee/weight_estimate.py`（瘦身为从 pack_recommend 导入 PackRecommender，保留 ship_key 解析）
  - `courier_fee/bill_services.py`（OPT_02/03/04/05 全流程、generate_corrected_zip、_ensure_bill_tables 迁移）
  - `courier_fee/services.py`（底单导入保留非日期行；计费规则表加 weight_tolerance_pct）
  - `courier_fee/table_schemas.py`（展示列、默认计费规则加允差）
  - `templates/courier_fee.html`（计费标准加「重量允差%」列）
- 修改原因：原重量核对用固定包材常量+百分比范围，对轻货误判率高达45%(9081条)；需按真实箱型匹配精确预估并与 VBA 口径对齐（只对快递多收费的超重较真）。底单导入丢弃退货占号行导致空白异常虚高。包装推荐算法此前页头打印(JS)与快递费(Python)各一份，后端单一源化以便统一维护。
- 影响范围：courier_fee 全模块、label_print 推荐前端改为调后端接口（行为：实时本地计算→防抖请求后端）；共用 label_weights/label_sizes/label_packing_*/label_pack_* 等表（只读）。
- 是否涉及数据库：是（运行时迁移：courier_fee_bills 加列 ship_content_key；courier_fee_pricing_rules 加列 weight_tolerance_pct；均 CREATE TABLE IF NOT EXISTS + ALTER TABLE try/except 幂等。底单/账单业务数据需重新导入并重新运行计算以生效）
- 是否需要回滚：否（新增列向后兼容；如需回滚代码，旧列保留不影响）

## [2026-06-09 21:38] 修改记录
- 修改内容：将快递费模块及包装推荐后端单一源化等本地改动提交并推送到 GitHub `main`（`5671e55` → `568b8cb`），随后更新西班牙马德里服务器 `208.85.17.83` 运行新代码。
  1. 提交内容：新增 courier_fee 整模块（routes/services/bill_services/table_schemas/weight_estimate + __init__）、新增 label_print/pack_recommend.py（包装推荐+预估重量唯一算法源）、label_print/routes.py 加 /label_print/api/recommend 接口、templates/courier_fee.html、templates/label_print.html（删约340行重复JS改调后端）、app.py 注册蓝图、auth/services.py 加 courier_fee 权限key/标签、templates/index.html 加菜单入口、.gitignore 排除敏感项、PROJECT_MEMORY.md。
  2. .gitignore 新增忽略：temp/（含200MB真实账单/底单数据）、data_local_backup_*/、backups/、*.pid、flask_local*.log；确认提交未包含任何 temp/、data/、*.db、备份或日志。
  3. 服务器：git pull origin main 快进到 568b8cb；重启前用 .venv/bin/python 自检 courier_fee + pack_recommend 导入成功（依赖齐全）；pkill 旧 app.run 进程后 setsid 启动新 production 进程（PID 300618，0.0.0.0:5001, debug=False）。验证 /courier_fee/、/label_print/api/recommend、/label_print/ 均返回 302（已注册需登录），公网 http://208.85.17.83:5001/ 返回 302，服务器 HEAD=568b8cb。
- 修改文件：GitHub main；服务器 /root/my-flask-project；本地 .gitignore、PROJECT_MEMORY.md
- 修改原因：需要把快递费模块与包装推荐单一源化改动发布到 GitHub 并让马德里服务器运行新代码。
- 影响范围：GitHub main、马德里服务器代码与运行进程；data/ 为 gitignore，拉取未触碰服务器业务数据。
- 是否涉及数据库：否（代码部署；服务器 courier_fee 相关表将于首次访问时自动创建，本次未写业务数据）
- 是否需要回滚：是（服务器 `git reset --hard 5671e55` 后重启可回退；GitHub 可 revert 568b8cb）
- 待办（服务器端人工）：1) 管理员给相关用户授予「快递费计算」模块权限；2) 在服务器端重新导入底单+账单并运行计算。

## [2026-06-13 16:35] 修改记录
- 修改内容：页头打印包装推荐后端算法新增一批仓库实际箱型样本校准；异形货物等效尺寸改为按一正一反成对堆叠估算，2 件高度按「原始高 + 低端高」计算，奇数多出的 1 件按原始高度补上，且堆叠高度锁定为箱高方向，避免 184 数量变化但推荐箱型长期不变；同步更新装箱规则文档。
- 修改文件：label_print/pack_recommend.py；PACKING_RECOMMENDATION_RULES.md；PROJECT_MEMORY.md
- 修改原因：184 为牙膏/三角状异形货物，一端高约 35mm、另一端约 5mm，原通用异形公式对多件堆叠过度压缩；同时需要用新增真实装箱数据进一步校准页头打印和快递费共用的包装推荐结果。
- 影响范围：页头打印模块和快递费模块共用的包装推荐、预估重量箱型选择；不修改数据库结构，不改货物尺寸原始数据，不影响 WPS 读取和打印版式。
- 是否涉及数据库：否
- 是否需要回滚：是
## [2026-06-13 16:48] 修改记录
- 修改内容：将包装推荐与快递费账单修正相关最新本地改动提交并推送到 GitHub `main`，业务提交为 `b17a932`；随后在西班牙马德里服务器 `208.85.17.83` 的 `/root/my-flask-project` 执行 `git pull origin main`，从 `76bf2c9` 快进到 `b17a932` 并重启 Flask 服务。重启后新进程 `482433` 监听 `0.0.0.0:5001`，服务器本机 `/`、`/courier_fee/`、`/label_print/` 均返回 302 登录跳转。
- 修改文件：GitHub `main`；服务器 `/root/my-flask-project`；`PROJECT_MEMORY.md`
- 修改原因：用户要求将当前最新代码推送 GitHub 仓库，并更新西班牙服务器运行新代码。
- 影响范围：GitHub `main` 与西班牙服务器线上 Flask 应用代码及运行进程；未提交本地 `AGENTS.md`、`flask_local.out.log`，未覆盖服务器 `data/` 业务数据。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-16 15:47] 修改记录
- 修改内容：修复页头打印 WPS 今日记录偶发重复显示。WPS 记录去重从包含整行 JSON/行号的易变 `row_hash` 改为按来源、业务日期、提交时间、归一化货物清单生成稳定业务指纹；读取今日记录前会合并同一业务指纹下的历史重复记录，并保留/汇总已解析、已打印状态和打印历史关联。归一化时忽略货物清单中连续分隔线，避免截图中同一货物清单夹带横线后被误判为不同记录。同时将 WPS 来源显示名由“WPS主表 / WPS补充表”改为“主播样品 / 售后补发”。
- 修改文件：label_print/routes.py；PROJECT_MEMORY.md
- 修改原因：旧去重键包含 WPS 行号、表头和整行字段，WPS 行移动、重复提交、隐藏字段变化或货物文本夹带分隔线时，会把同一业务记录拆成多条，导致页面出现一条已解析/已打印、一条未解析/未打印的重复行。
- 影响范围：仅页头打印模块 WPS 今日记录读取、入库去重、今日列表展示和打印历史关联修正；不修改 WPS 原表，不改变打印版式、解析规则和包装推荐算法。
- 是否涉及数据库：是（不改表结构；访问 WPS 今日记录时会合并 `label_wps_records` 中同一业务指纹的重复记录，并把重复记录的 `label_print_history.wps_record_id` 指向保留记录）
- 是否需要回滚：是

## [2026-06-16 15:53] 修改记录
- 修改内容：页头打印 WPS 记录解析后打印时，若总票数输入框为空或为 0，自动按 1 票处理并回填输入框；手工打印路径仍保持必须填写总票数的校验。
- 修改文件：templates/label_print.html；PROJECT_MEMORY.md
- 修改原因：WPS 记录通常按单条提交打印，用户不希望解析打印时还必须手工设置总票数。
- 影响范围：仅页头打印模块选中 WPS 今日记录后的打印流程；不影响手工货物录入打印、不修改 WPS 数据、不修改数据库结构。
- 是否涉及数据库：否
- 是否需要回滚：是

## [2026-06-16 15:57] 修改记录
- 修改内容：将页头打印 WPS 重复记录修复、WPS 来源改名、WPS 解析打印默认 1 票等改动提交并推送到 GitHub `main`，业务提交为 `f3fc59b`；随后在西班牙马德里服务器 `208.85.17.83` 的 `/root/my-flask-project` 执行 `git pull --ff-only origin main`，从 `e30cb23` 快进到 `f3fc59b`，并用 `.venv/bin/python` 重启 Flask 服务。重启后服务器 HEAD 为 `f3fc59b`，新进程 `645918` 监听 `0.0.0.0:5001`，服务器本机 `/` 与 `/label_print/` 均返回 302 登录跳转。
- 修改文件：GitHub `main`；服务器 `/root/my-flask-project`；PROJECT_MEMORY.md
- 修改原因：用户要求将页头打印相关修复上传 GitHub，并通过仓库更新西班牙服务器运行新代码。
- 影响范围：GitHub `main` 与西班牙服务器线上 Flask 应用代码及运行进程；未覆盖服务器 `data/` 业务数据。
- 是否涉及数据库：否（代码部署；新代码访问 WPS 今日记录时可能按业务指纹合并页头打印 WPS 重复记录）
- 是否需要回滚：是

## [2026-06-17 15:30] 修改记录
- 修改内容：新增“海外旗舰（抖音）”模块，复用抖音店铺公共页面、四表导入、原始数据导出、佣金汇总导出和达人/团长明细导出能力。新增独立蓝图 `/douyin_shop_overseas/`、权限 key `douyin_shop_overseas`、首页入口和独立数据表前缀 `dy_overseas`。公共抖音服务层新增海外资金结算文件格式分支：`海外结算*.csv` 按“动账时间/动账流水号/动账方向/动账账户/动账金额/动账摘要/订单号/子订单号/下单时间/商品ID/税费/业务类型/结算金额(元)/汇率/币种/结算外币金额/订单实付(元)/达人补贴(元)/平台补贴(元)/平台补贴外币金额/退款(元)/平台服务费(元)/佣金(元)/招商服务费(元)/供应链费用(元)/预留税费(元)/站外推广费(元)/供应链欠款抵扣(元)/分期服务费(元)/是否免佣/免佣金额”映射入海外资金表，并以动账流水号防重；佣金汇总/明细导出在海外资金表不含达人名称时，按订单号/子订单号关联订单表补齐达人昵称和达人ID。同步清洗平台 CSV 文本前导单引号，避免海外动账时间无法按日期筛选。
- 修改文件：app.py；auth/services.py；douyin_shop_overseas/__init__.py（新增）；douyin_shop_common/__init__.py；douyin_shop_common/services.py；douyin_shop_common/table_schemas.py；templates/index.html；templates/douyin_shop.html；PROJECT_MEMORY.md
- 修改原因：用户需要仿照香娜露儿/幕莲蔓抖音模块新增“海外旗舰（抖音）”模块，四张表功能用途一致，但海外结算系列文件的资金流水格式与原两个抖音模块不同，需要单独适配。
- 影响范围：新增海外旗舰抖音模块及其权限/首页入口/独立数据表；抖音公共服务层新增海外资金流水格式分支，并调整后续导入文本清洗去掉平台 CSV 前导单引号。香娜露儿和幕莲蔓仍默认使用标准资金结算格式。
- 是否涉及数据库：是（首次访问/导入海外模块时会自动创建 `dy_overseas_orders`、`dy_overseas_fund_flow`、`dy_overseas_commission`、`dy_overseas_merchant`、`dy_overseas_data_status`；本次功能验证使用临时 SQLite，路由注册检查未导入海外业务数据）
- 是否需要回滚：是

## [2026-06-17 15:55] 修改记录
- 修改内容：补强抖音店铺公共状态读取逻辑，进入模块首页读取数据状态时同步确保订单、资金结算、佣金订单明细、招商订单明细四张业务表存在并补齐字段；海外旗舰首次打开页面即可自动创建 `dy_overseas_orders`、`dy_overseas_fund_flow`、`dy_overseas_commission`、`dy_overseas_merchant` 与 `dy_overseas_data_status`，无需等到首次导入才建表。
- 修改文件：douyin_shop_common/services.py；PROJECT_MEMORY.md
- 修改原因：复核海外旗舰模块线上首次运行行为时发现原逻辑首次打开页面只创建数据状态表，业务表在首次导入时才自动创建；为确保线上第一次打开模块即可加载新表，补齐首页状态读取时的业务表建表保障。
- 影响范围：香娜露儿、幕莲蔓、海外旗舰三个抖音店铺模块首页状态读取；使用 `CREATE TABLE IF NOT EXISTS` 与补列逻辑，既有表和数据不被覆盖。
- 是否涉及数据库：是（首次打开抖音店铺模块页面时可能自动创建/补齐对应店铺的四张业务表和状态表；本次验证仅使用临时 SQLite）
- 是否需要回滚：是

## [2026-06-17 16:04] 修改记录
- 修改内容：将海外旗舰抖音订单表从标准抖音订单 schema 中独立出来，新增海外订单专用字段 `sku_id`（货品ID）、`serial_no`（序列号）、`is_product_unit_price_tax_included`（商品单价是否含税）、`tax_fee`（税费）。`douyin_shop_overseas` 显式声明 `order_format='overseas'`，公共服务层按店铺配置选择订单表字段、建表补列、导入写库、防重和原始数据导出字段选择器；香娜露儿、幕莲蔓仍使用标准订单 schema。已用真实海外订单 CSV 抽样验证：首次建表生成 77 个业务字段（含新增 4 字段），导入后可读到货品ID、商品单价是否含税、税费，重复导入第二次写入 0。
- 修改文件：douyin_shop_overseas/__init__.py；douyin_shop_common/__init__.py；douyin_shop_common/services.py；douyin_shop_common/table_schemas.py；PROJECT_MEMORY.md
- 修改原因：用户确认海外订单 CSV 为 77 列，多出的 `货品ID`、`序列号`、`商品单价是否含税`、`税费` 需要入库并可导出，不能简单忽略或强行套用标准抖音订单 schema。
- 影响范围：海外旗舰抖音订单表建表/补列/导入/导出字段；不改变香娜露儿、幕莲蔓订单表字段。海外结算文件仍按海外资金流水分支读取；标准抖音资金结算文件仍保留跳过第 2 行说明行的特例。
- 是否涉及数据库：是（海外旗舰首次打开或导入时会为 `dy_overseas_orders` 创建/补齐新增 4 个订单字段；本次验证仅使用临时 SQLite）
- 是否需要回滚：是

## [2026-06-18 12:02] 修改记录
- 修改内容：新增“豁免管理”模块，包含香娜露儿豁免管理与慕莲蔓豁免管理两个 TAB；新增 `creator_exemptions` 达人豁免数据表，使用 `brand` 字段区分香娜露儿和慕莲蔓；香娜露儿按截图初始化 60 条豁免数据，包含生效中和已结束记录；页面支持达人渠道/昵称/UID 模糊查询、状态筛选、生效日期和结束日期组合筛选、新增、编辑、停止和删除，暂不提供导入导出功能。
- 修改文件：app.py；auth/services.py；templates/index.html；exemption_management/__init__.py；exemption_management/routes.py；exemption_management/services.py；templates/exemption_management.html；PROJECT_MEMORY.md
- 修改原因：用户需要将达人豁免截图数据沉淀到系统中管理，并支持后续手工维护和查询。
- 影响范围：新增独立豁免管理模块、权限入口和数据库表；不影响现有抖音店铺、快手澳柯、快递费、发票等模块。
- 是否涉及数据库：是
- 是否需要回滚：是

## [2026-06-18 12:12] 修改记录
- 修改内容：补充“豁免管理”模块慕莲蔓初始截图数据，新增 9 条慕莲蔓已结束豁免记录；同时将达人豁免初始化逻辑改为按品牌记录一次性 seed 标记，新增 `creator_exemption_seed_state` 标记表，确保每个品牌初始数据只在未初始化时写入，后续刷新、编辑或删除业务数据不会自动补回旧截图数据。
- 修改文件：exemption_management/services.py；PROJECT_MEMORY.md
- 修改原因：用户补充慕莲蔓豁免截图初始数据，并要求初始数据仅在首次运行添加数据表时保存，之后不得影响已有数据表。
- 影响范围：仅影响豁免管理模块首次初始化数据逻辑；不影响现有豁免数据的手工新增、编辑、停止、删除功能，不影响其他业务模块。
- 是否涉及数据库：是
- 是否需要回滚：是

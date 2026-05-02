# 上传与文件系统变更记录

本文件记录本聊天后续所有涉及上传文件、临时文件、归档目录、清理策略、文件系统回滚路径的修改。不得覆盖历史，只能追加。

## [2026-05-02 11:47] 文件系统修改记录
- 修改内容：建立统一 Excel 上传暂存机制，微信小店订单/资金流水/售后导入与发票核对应开金额导入先保存至独立批次临时目录，再由导入逻辑读取服务器本地暂存文件。
- 涉及目录：
  - data/upload_staging/tmp/wechat_shop/orders/
  - data/upload_staging/tmp/wechat_shop/fund_flows/
  - data/upload_staging/tmp/wechat_shop/aftersales/
  - data/upload_staging/tmp/invoicing/expected_amounts/
- 涉及文件：
  - common/upload_staging.py
  - wechat_shop/routes.py
  - wechat_shop/services.py
  - invoicing/routes.py
- 文件保留策略：Excel 原始文件只在单次导入批次中短暂暂存；导入成功或失败后立即删除当前批次目录。每次暂存前自动清理超过 2 小时的孤儿批次目录。
- 长期记录策略：仅在 data/upload_staging/import_log.jsonl 中保留批次号、导入类型、文件名、状态、错误摘要和清理结果，不保留 Excel 原件。
- 回滚路径：回滚上述代码文件，删除 data/upload_staging/ 目录；数据库无需回滚。

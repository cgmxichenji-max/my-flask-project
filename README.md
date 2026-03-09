# my-flask-project
A simple Flask web application
这是一次测试编辑：如果你现在能看到这句话，说明本次写入成功。
# 包材库存管理系统

这是一个用于管理 **包材库存** 的 Flask 小型系统，用于记录和管理包装材料的采购、库存和相关信息。

项目主要用于个人内部管理和学习 Flask + GitHub 的开发流程。

---

# 项目运行方法

第一次在新电脑运行项目，需要先安装依赖：

```bash
pip install -r requirements.txt

#启动程序

python3 app.py

# 每次工作前（同步最新代码）

如果在多台电脑上开发，建议每次开始工作前先执行：

```bash
git pull
```

这样可以把 GitHub 上最新的代码同步到本地，避免代码冲突。

# 每次工作后

```bash
git add .
git commit -m "更新说明"
git push
```

# Git 忽略说明

项目已配置 `.gitignore`，会忽略以下不需要上传到 GitHub 的文件：

- `_excel_cache/`
- `*.xlsx`
- `*.xls`
- `*.xlsm`
- `~$*.xlsx`
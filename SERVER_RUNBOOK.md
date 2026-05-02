# 服务器部署与手工运维命令手册

本文档用于在东京服务器或上海单位电脑上手工部署、启动、停止、备份、恢复本 Flask 项目，避免临时操作时命令写错。

## 1. 当前服务器信息

### 东京服务器

```text
IP: 108.61.200.244
用户: root
项目路径: /root/my-flask-project
GitHub: https://github.com/cgmxichenji-max/my-flask-project.git
Flask 端口: 5001
公网访问:
  http://108.61.200.244:5001/auth/login
  http://108.61.200.244/auth/login
```

登录：

```bash
ssh root@108.61.200.244
```

进入项目目录：

```bash
cd /root/my-flask-project
```

## 2. 东京服务器常用检查命令

### 查看当前代码版本

```bash
cd /root/my-flask-project
git log --oneline -5
git status
```

### 查看服务是否在运行

```bash
ps -ef | awk '$8=="python3" && $9=="app.py" {print}'
ps -ef | grep '[p]ython3 -c'
```

### 查看 5001 端口监听

```bash
ss -ltnp | grep ':5001' || netstat -ltnp | grep ':5001'
```

### 查看启动日志

```bash
cd /root/my-flask-project
tail -100 flask.log
```

持续观察日志：

```bash
cd /root/my-flask-project
tail -f flask.log
```

### 测试登录页是否正常

```bash
curl -s -o /tmp/login.html -w '%{http_code}\n' http://127.0.0.1:5001/auth/login
```

返回 `200` 表示 Flask 本机访问正常。

公网测试：

```bash
curl -s -o /dev/null -w '5001=%{http_code}\n' http://108.61.200.244:5001/auth/login
curl -s -o /dev/null -w 'nginx=%{http_code}\n' http://108.61.200.244/auth/login
```

### 查看 nginx 上传大小限制

Excel/PDF 上传经 nginx 反向代理进入 Flask。当前站点配置要求包含：

```nginx
client_max_body_size 200m;
```

检查命令：

```bash
nginx -T 2>/dev/null | grep -n 'client_max_body_size\|server_name gqjcore'
```

如果上传时出现 `413 Request Entity Too Large`，先确认 `/etc/nginx/sites-available/flaskapp` 的 `server` 块内是否有上述配置，再执行：

```bash
nginx -t
systemctl reload nginx
```

2026-05-02 调整前备份文件：

```text
/etc/nginx/sites-available/flaskapp.backup_before_upload_limit_20260502_042757
```

## 3. 东京服务器启动 / 停止 / 重启

### 推荐启动方式（debug 关闭）

```bash
cd /root/my-flask-project
nohup python3 -c "from app import app; print('>>> production-ish start: debug off', flush=True); app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)" > flask.log 2>&1 &
sleep 4
tail -60 flask.log
```

### 停止服务

不要用宽泛的 `pkill -f "python3 app.py"`，容易误杀当前 SSH 命令。使用下面这种更精确的方式：

```bash
cd /root/my-flask-project
pids=$(ps -ef | awk '$8=="python3" && $9=="app.py" {print $2}')
if [ -n "$pids" ]; then
  kill $pids
fi

pids=$(ps -ef | grep '[p]ython3 -c' | awk '{print $2}')
if [ -n "$pids" ]; then
  kill $pids
fi
```

### 重启服务

```bash
cd /root/my-flask-project

pids=$(ps -ef | awk '$8=="python3" && $9=="app.py" {print $2}')
if [ -n "$pids" ]; then
  kill $pids
fi

pids=$(ps -ef | grep '[p]ython3 -c' | awk '{print $2}')
if [ -n "$pids" ]; then
  kill $pids
fi

sleep 2
nohup python3 -c "from app import app; print('>>> production-ish start: debug off', flush=True); app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)" > flask.log 2>&1 &
sleep 4
tail -60 flask.log
curl -s -o /tmp/login.html -w '%{http_code}\n' http://127.0.0.1:5001/auth/login
```

## 4. 东京服务器代码更新

先进入项目目录：

```bash
cd /root/my-flask-project
```

备份当前完整项目：

```bash
cd /root
ts=$(date +%Y%m%d_%H%M%S)
tar -czf /root/my-flask-project_backup_before_update_$ts.tar.gz my-flask-project
ls -lh /root/my-flask-project_backup_before_update_$ts.tar.gz
```

更新代码到 GitHub main 最新版：

```bash
cd /root/my-flask-project
git fetch origin main
git reset --hard origin/main
git log --oneline -1
```

安装/更新依赖：

```bash
cd /root/my-flask-project
pip3 install -r requirements.txt
```

重启服务：

```bash
cd /root/my-flask-project

pids=$(ps -ef | awk '$8=="python3" && $9=="app.py" {print $2}')
if [ -n "$pids" ]; then
  kill $pids
fi

pids=$(ps -ef | grep '[p]ython3 -c' | awk '{print $2}')
if [ -n "$pids" ]; then
  kill $pids
fi

sleep 2
nohup python3 -c "from app import app; print('>>> production-ish start: debug off', flush=True); app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)" > flask.log 2>&1 &
sleep 4
curl -s -o /tmp/login.html -w '%{http_code}\n' http://127.0.0.1:5001/auth/login
```

## 5. 东京服务器数据备份

项目数据主要包括：

```text
data/main.db
data/invoice_pdfs/
data/invoice_pdfs_pending/
```

备份完整 data 目录：

```bash
cd /root/my-flask-project
ts=$(date +%Y%m%d_%H%M%S)
tar -czf /root/my-flask-project_data_backup_$ts.tar.gz data
ls -lh /root/my-flask-project_data_backup_$ts.tar.gz
```

只备份数据库：

```bash
cd /root/my-flask-project
ts=$(date +%Y%m%d_%H%M%S)
cp data/main.db data/main_backup_$ts.db
ls -lh data/main_backup_$ts.db
```

查看数据库关键表行数：

```bash
cd /root/my-flask-project
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('data/main.db')
for table in ['invoice', 'expected_amount', 'customer', 'customer_alias', 'billing_entity', 'user']:
    print(table, conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
conn.close()
PY
```

查看 PDF/JSON 文件数量：

```bash
cd /root/my-flask-project
python3 - <<'PY'
import os
pdf = 0
json_count = 0
appledouble = 0
for root, dirs, files in os.walk('data'):
    for name in files:
        if name.lower().endswith('.pdf'):
            pdf += 1
        if name.lower().endswith('.json'):
            json_count += 1
        if name.startswith('._'):
            appledouble += 1
print('pdf_files', pdf)
print('json_files', json_count)
print('appledouble_files', appledouble)
PY
```

## 6. 从本机同步数据到东京服务器

在本机项目目录执行。

### 生成干净数据包

```bash
cd /Users/sunrise.ji/Dev/MyWork/my-flask-project-github
ts=$(date +%Y%m%d_%H%M%S)
COPYFILE_DISABLE=1 tar --no-xattrs --exclude='._*' --exclude='.DS_Store' \
  -czf /tmp/my_flask_project_data_$ts.tar.gz \
  data/main.db data/invoice_pdfs data/invoice_pdfs_pending
ls -lh /tmp/my_flask_project_data_$ts.tar.gz
```

检查包内文件数量：

```bash
tar -tzf /tmp/my_flask_project_data_*.tar.gz | awk '
BEGIN { pdf=0; json=0; apple=0 }
{
  if (tolower($0) ~ /\.pdf$/) pdf++;
  if (tolower($0) ~ /\.json$/) json++;
  if ($0 ~ /\/\._/) apple++;
}
END {
  print "tar_pdf", pdf;
  print "tar_json", json;
  print "appledouble", apple;
}'
```

上传到东京：

```bash
scp /tmp/my_flask_project_data_YYYYMMDD_HHMMSS.tar.gz root@108.61.200.244:/tmp/my_flask_project_data_deploy.tar.gz
```

在东京服务器上应用数据包：

```bash
ssh root@108.61.200.244
cd /root/my-flask-project

ts=$(date +%Y%m%d_%H%M%S)
tar -czf /root/my-flask-project_data_backup_before_sync_$ts.tar.gz data
ls -lh /root/my-flask-project_data_backup_before_sync_$ts.tar.gz

rm -rf data/invoice_pdfs data/invoice_pdfs_pending
tar -xzf /tmp/my_flask_project_data_deploy.tar.gz -C /root/my-flask-project

find data -name '._*' -delete
```

重启服务：

```bash
cd /root/my-flask-project
pids=$(ps -ef | grep '[p]ython3 -c' | awk '{print $2}')
if [ -n "$pids" ]; then
  kill $pids
fi
sleep 2
nohup python3 -c "from app import app; print('>>> production-ish start: debug off', flush=True); app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)" > flask.log 2>&1 &
sleep 4
curl -s -o /tmp/login.html -w '%{http_code}\n' http://127.0.0.1:5001/auth/login
```

## 7. 从东京服务器恢复数据

查看已有备份：

```bash
ls -lh /root/my-flask-project_data_backup_*.tar.gz
ls -lh /root/my-flask-project_data_backup_before_sync_*.tar.gz
```

恢复某个 data 备份：

```bash
cd /root/my-flask-project

pids=$(ps -ef | grep '[p]ython3 -c' | awk '{print $2}')
if [ -n "$pids" ]; then
  kill $pids
fi

mv data data_broken_$(date +%Y%m%d_%H%M%S)
tar -xzf /root/要恢复的备份文件.tar.gz -C /root/my-flask-project

nohup python3 -c "from app import app; print('>>> production-ish start: debug off', flush=True); app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)" > flask.log 2>&1 &
sleep 4
curl -s -o /tmp/login.html -w '%{http_code}\n' http://127.0.0.1:5001/auth/login
```

## 8. 上海单位电脑手工部署方案

### 拉取代码

```bash
cd 你要放项目的目录
git clone https://github.com/cgmxichenji-max/my-flask-project.git
cd my-flask-project
git checkout main
git pull origin main
```

如果已经 clone 过：

```bash
cd my-flask-project
git fetch origin main
git reset --hard origin/main
```

### 安装依赖

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### 同步数据

从东京拉当前数据包：

```bash
scp root@108.61.200.244:/root/my-flask-project_data_current_20260428_170440.tar.gz .
tar -xzf my-flask-project_data_current_20260428_170440.tar.gz
```

确认文件存在：

```bash
ls -lh data/main.db
find data/invoice_pdfs -type f -name '*.pdf' | wc -l
find data/invoice_pdfs_pending -type f | wc -l
```

### 启动上海本地服务

```bash
cd my-flask-project
python3 -c "from app import app; app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)"
```

浏览器打开：

```text
http://127.0.0.1:5001/auth/login
```

### 上海本地验证

```bash
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('data/main.db')
for table in ['invoice', 'expected_amount', 'customer', 'customer_alias', 'billing_entity', 'user']:
    print(table, conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
conn.close()
PY
```

当前东京/本机预期行数：

```text
invoice 138
expected_amount 1412
customer 1086
customer_alias 111
billing_entity 4
user 4
```

## 9. 常见问题

### 依赖安装失败

先确认 `requirements.txt` 中是已验证版本：

```text
numpy==2.2.6
opencv-python-headless==4.12.0.88
pandas==2.2.3
pdfplumber==0.11.9
Pillow==12.2.0
PyMuPDF==1.27.2.2
```

重新安装：

```bash
python3 -m pip install -r requirements.txt
```

### 登录页 500 或打不开

看日志：

```bash
cd /root/my-flask-project
tail -100 flask.log
```

确认端口：

```bash
ss -ltnp | grep ':5001'
```

确认数据库存在：

```bash
ls -lh data/main.db
```

### 发票 PDF 打不开

确认 PDF 文件存在：

```bash
cd /root/my-flask-project
find data/invoice_pdfs -type f -name '*.pdf' | wc -l
find data/invoice_pdfs -type f -name '发票号.pdf'
```

### GitHub 更新后页面没变化

确认远端 commit：

```bash
cd /root/my-flask-project
git log --oneline -3
```

重启服务：

```bash
cd /root/my-flask-project
pids=$(ps -ef | grep '[p]ython3 -c' | awk '{print $2}')
if [ -n "$pids" ]; then
  kill $pids
fi
sleep 2
nohup python3 -c "from app import app; app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)" > flask.log 2>&1 &
```

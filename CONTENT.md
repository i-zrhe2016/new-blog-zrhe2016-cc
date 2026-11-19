# 文章数据与备份

线上 SQLite 数据库是文章、草稿、站点设置和账号等数据的主要存储。`content/` 是可选的旧格式导出和迁移资源目录，不再提交到 Git；现有本地文件不会因停止跟踪而删除。保存文章时默认不再自动导出 Markdown，必要时可显式设置 `PERSONAL_CONTENT_AUTO_EXPORT=True` 或运行 `python manage.py export_personal_content`。

## 备份

部署脚本安装并启动 `bearblog-backup.timer`，每天执行一次备份，并在部署迁移前立即备份。也可以在服务器上手动执行：

```bash
sudo systemctl start bearblog-backup.service
```

```bash
sudo systemctl status bearblog-backup.service bearblog-backup.timer
```

每次备份在 `/opt/bearblog/backups/backup-<UTC时间>-<随机值>/` 下包含 `database.db` 和 `assets.tar.gz`。数据库通过 SQLite backup API 在线生成一致快照并做完整性检查；资源包包含 `/opt/bearblog/content/assets` 下的迁移图片和图表。两者分别采集，不保证资源与数据库同时刻原子一致；操作期间避免修改迁移资源。数据库和备份包含草稿、账号及其他敏感数据，应限制访问。备份失败会使服务报错，查看 `journalctl -u bearblog-backup.service`。备份不会自动清理，需监控空间并定期复制到安全的异地存储，否则服务器或磁盘损坏可能同时损失原始数据和备份。外部对象存储中的文件不在此备份范围内，应另外备份。

自定义路径或手工执行：

```bash
python3 deploy/backup_database.py --database /opt/bearblog/data/dev.db --assets /opt/bearblog/content/assets --destination /opt/bearblog/backups
```

## 恢复

恢复会覆盖现有数据。先停止所有访问数据库的应用和后台任务，保存当前数据库及其 WAL/SHM 文件，并选择、检查所需备份。下面的命令在生产服务器上以有权限的用户执行；将 `BACKUP` 替换为实际备份目录。

```bash
BACKUP=/opt/bearblog/backups/backup-YYYYMMDDTHHMMSSZ-ID
```

```bash
cd /opt/bearblog && docker compose stop bearblog bearblog-private
```

停止其他数据库访问后，保留现有数据库和 WAL/SHM 文件的副本，再删除原位置的 WAL/SHM 文件，避免旧日志影响恢复。然后复制快照和资源：

```bash
cp "$BACKUP/database.db" /opt/bearblog/data/dev.db
```

```bash
tar -xzf "$BACKUP/assets.tar.gz" -C /opt/bearblog/content
```

确认数据库文件权限适合容器用户后，按部署流程执行迁移、`collectstatic`，再启动容器并检查文章和图片。恢复资源包会覆盖同名文件，但不会删除备份中没有的现有资源。先在隔离环境演练恢复，并确认数据库和资源完整。数据库快照不包含应用配置、`.env` 或外部对象存储。

旧 Git 历史仍含曾经提交的文章与草稿，停止跟踪不会删除历史；如仓库曾公开，按需另行处理已发布的数据。

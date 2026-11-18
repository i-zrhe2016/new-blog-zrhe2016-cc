# 个人博客内容与 Git

博客在线运行仍使用 SQLite（deploy 上 `/opt/bearblog/data/dev.db`）。文章不再只存在数据库中：个人博客模式（`SINGLE_BLOG=True`）默认把当前内容导出到项目的 `content/`，保存文章和站点设置后自动更新文件。

## 仓库里的内容

- `content/posts/<uid>.md`：每篇文章、草稿、独立页面一份文件。开头 `---` 之间是 JSON 元数据，后面是原始 Markdown 正文。稳定 UID 用于文件名，修改标题或网址不会换文件。
- `content/blog.json`：首页、导航、样式、SEO、站点配置，以及建站和修改时间。
- `content/manifest.json`：受管理的文章文件清单；删除文章后会更新清单并删除对应文件。
- `content/assets/`：迁移的图片与 PlantUML 图。收集静态文件时映射为 `/static/migrated/`，与正文原有链接对应。

初始迁移包含 39 篇已发布文章、2 篇草稿和 1 个 About 页面。标签、发布状态、文章网址、重定向别名与原有时间保留。草稿也会进入 Git，公开仓库时草稿内容也会公开。

账号、密码散列、会话、邮件订阅、访问统计、投票和服务器密钥不属于内容快照，不进入 Git；恢复内容前需要先创建自己的账号。SQLite、`.env`、同步锁及同步记录均被忽略。

## 在线写作后同步到当前项目

服务器和这份本地项目是两个目录。在线保存会更新服务器的 `/opt/bearblog/content`，提交 Git 前，在本项目根目录执行：

```bash
python -I scripts/sync_personal_content.py
```

命令通过 `tailscale ssh root@deploy` 先导出最新内容，再按 SHA-256 校验并只下载变化的文件。它不下载数据库或密钥，不执行 Git 提交。文章删除也会在下次同步体现。第一次运行会建立被 Git 忽略的同步记录，以后若本地文件有冲突，命令会停止，避免覆盖本地编辑。确认以服务器为准时才使用：

```bash
python -I scripts/sync_personal_content.py --accept-server
```

检查 `git diff` 后，将 `content/` 和相关代码一起提交即可。此项目没有自动提交、自动推送或远程仓库地址配置；这些操作由使用者决定。

```bash
git add content CONTENT.md blogs conf/settings.py scripts .gitignore
```

## 从 Git 内容恢复

先安装项目依赖、配置环境变量、执行 Django migrations，并创建用于管理博客的账号。然后导入文件：

```bash
python manage.py import_personal_content content --owner YOUR_USERNAME
```

默认只允许恢复到空博客，防止意外覆盖现有内容。恢复后运行：

```bash
python manage.py collectstatic --noinput
```

个人模式下 `content/assets/` 会成为迁移静态资源的来源；无需另找旧服务器上的图片。

## 修改 Markdown 后应用到网站

文件不会在每次请求时自动读回数据库。修改文件后，明确执行导入命令更新已有博客：

```bash
python manage.py import_personal_content content --owner YOUR_USERNAME --update
```

`--update` 更新清单中出现的文章，并保留数据库中清单外的文章。若确实希望将 Git 中删除的文章同步删除，才加上 `--delete-missing`。导入前备份在线数据库。不要同时进行在线编辑和文件导入。

线上执行这些命令时需要使用包含相应 `content/` 文件的部署目录或容器；本地文件导入只会修改本地数据库。

## 导出与可靠性

可随时从数据库重新生成快照：

```bash
python manage.py export_personal_content content
```

默认目录可通过 `PERSONAL_CONTENT_DIR` 覆盖。导出先取得一致的数据库快照，单文件使用临时文件替换；多文件使用锁避免两个导出同时写入。在线保存提交数据库后执行导出；若文件系统不可写，会记录错误，数据库保存仍成功。deploy 配置每分钟重新导出，以便恢复遗漏；同步命令也会在下载前重新导出。数据库提交和文件导出不是同一个原子事务，导出失败期间应先修复并重试，再进行 Git 提交。

这是当前内容的可恢复快照。Git 保留的是实际提交过的版本：两次提交之间的每次在线编辑不会自动成为一个 Git 版本；过去数据库里已被覆盖、未曾备份的编辑记录也无法凭空恢复。旧 Astro 仓库的历史仍在旧仓库中，本次迁移不会伪造或重写它。

## 验证

内容存储的测试涵盖正文及时间精度的完整往返恢复、草稿和页面、保存/删除、事务回滚、导出失败后重试，以及显式文件更新和删除：

```bash
python manage.py test blogs.test_content_store
```

同步工具的独立测试覆盖本地删除冲突、下载期间的编辑、损坏内容和并发同步：

```bash
python -I scripts/test_sync_personal_content.py
```

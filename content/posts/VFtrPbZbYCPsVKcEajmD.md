---
{
  "uid": "VFtrPbZbYCPsVKcEajmD",
  "title": "k9s介绍",
  "slug": "k9s",
  "alias": "posts/k9s",
  "published_date": "2025-11-29T13:36:00+00:00",
  "all_tags": "[]",
  "publish": true,
  "discoverable": false,
  "is_page": false,
  "canonical_url": "",
  "meta_description": "k9s是kubectl的可视化工具，能够更轻松地浏览、观察和管理已部署的应用程序，可以代替一部分需要kubectl手动输入的命令，简化操作。 快速安装 curl -sS [https://webi.sh/k9s](https://webi.sh/k9s) | sh; source ~/.config/envman/PA",
  "meta_image": "",
  "lang": "",
  "class_name": "",
  "first_published_at": "2025-11-29T13:36:00+00:00",
  "last_modified": "2026-11-18T07:44:30.205365+00:00"
}
---
k9s是kubectl的可视化工具，能够更轻松地浏览、观察和管理已部署的应用程序，可以代替一部分需要kubectl手动输入的命令，简化操作。

### 快速安装

```text
curl -sS [https://webi.sh/k9s](https://webi.sh/k9s) | sh; 
source ~/.config/envman/PATH.env

```

### 使用命令

:pod

查看部署的pods

![Snipaste_2025-11-30_17-24-49](/static/migrated/images/bearblog/5f0e62842ff8b24749e5.png)

l 查看pod的log日志
![2](/static/migrated/images/bearblog/1e42ffce6f847f9980ea.png)

/ 搜索显示的内容

: 切换资源

:alias 查看所有资源

![3](/static/migrated/images/bearblog/1afc695e883be85cdd3c.png)

? 查看所有命令
![4](/static/migrated/images/bearblog/847f2bd6e104d8bd62bb.png)

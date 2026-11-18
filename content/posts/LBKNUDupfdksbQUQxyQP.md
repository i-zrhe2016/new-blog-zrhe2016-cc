---
{
  "uid": "LBKNUDupfdksbQUQxyQP",
  "title": "使用ttyd将shell公开在web访问",
  "slug": "ttydshellweb",
  "alias": "posts/ttydshellweb",
  "published_date": "2025-10-02T13:34:00+00:00",
  "all_tags": "[]",
  "publish": true,
  "discoverable": false,
  "is_page": false,
  "canonical_url": "",
  "meta_description": "安装 snap install ttyd --classic 启动 ttyd -W -p 8889 bash 在浏览器中访问： http://IP:8889 好处就是shell可以直接在浏览器中访问，国外节点无需配置代理即可加速",
  "meta_image": "",
  "lang": "",
  "class_name": "",
  "first_published_at": "2025-10-02T13:34:00+00:00",
  "last_modified": "2026-11-18T07:44:30.257853+00:00"
}
---
安装

```text
snap install ttyd --classic

```

启动

```text
ttyd -W -p 8889 bash

```

在浏览器中访问：

```text
http://IP:8889

```

好处就是shell可以直接在浏览器中访问，国外节点无需配置代理即可加速

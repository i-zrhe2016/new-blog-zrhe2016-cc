---
{
  "uid": "PactNGXhCTnXDvPKTxLh",
  "title": "PlantUML 图表示例",
  "slug": "plantuml-example",
  "alias": "posts/plantuml-example",
  "published_date": "2026-10-13T08:00:00+00:00",
  "all_tags": "[\"plantuml\"]",
  "publish": false,
  "discoverable": false,
  "is_page": false,
  "canonical_url": "",
  "meta_description": "用时序图说明浏览器如何读取静态博客页面。",
  "meta_image": "",
  "lang": "",
  "class_name": "",
  "first_published_at": null,
  "last_modified": "2026-11-18T07:44:30.243247+00:00"
}
---
以下时序图描述一次静态博客访问。图表在本地生成，页面直接加载仓库中的 SVG。

![Browser requests a static blog page](/static/migrated/diagrams/plantuml/1e45e02f-7441853d-8a6fae68-60915137-c31a5025-a95ffd6c-6f603333-fcee1b06.svg)
普通代码块仍然显示为代码：

```text
browser -> assets: GET /posts/article/
```

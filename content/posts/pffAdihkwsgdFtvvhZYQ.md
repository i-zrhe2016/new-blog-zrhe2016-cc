---
{
  "uid": "pffAdihkwsgdFtvvhZYQ",
  "title": "写代码前，先搜 GitHub",
  "slug": "gitpilfer-search-github-before-coding",
  "alias": "posts/gitpilfer-search-github-before-coding",
  "published_date": "2026-11-04T10:00:00+00:00",
  "all_tags": "[\"AI\", \"GitHub\", \"开源\", \"Skill\"]",
  "publish": true,
  "discoverable": false,
  "is_page": false,
  "canonical_url": "",
  "meta_description": "GitPilfer 提倡先搜索和评估 GitHub 上的现有实现，再决定复用、修改还是从零编写。",
  "meta_image": "",
  "lang": "",
  "class_name": "",
  "first_published_at": "2026-11-04T10:00:00+00:00",
  "last_modified": "2026-11-18T07:44:30.186885+00:00"
}
---
使用 Claude Code、Codex 编程时，很多人习惯让 AI 从零实现功能。

但 GitHub 上可能早已有成熟的开源代码。直接复用，不仅能减少代码生成，还可能节省调试消耗的 Token。

## GitPilfer：先搜索，再写代码

[GitPilfer](https://github.com/pilgrimdelamare/GitPilfer) 是一个面向 AI 编程工具的 Skill。

核心原则：先搜索 GitHub，找到合适的实现就复用，找不到再自己写。

![搜索、评估并复用现有实现的流程](/static/migrated/diagrams/plantuml/7a3a9c18-82cf940a-a1011e04-8af6fb03-d46570af-008217be-80915300-2cb1cac5.svg)
## 为什么能节省 Token？

从零编写需要生成代码、探索实现方案，还可能反复调试。

复用成熟代码则把工作转向搜索、筛选和集成。

![从零编写和复用成熟代码的 Token 消耗对比](/static/migrated/diagrams/plantuml/41e7cf52-1efb3899-ce731740-11ec367c-efe7f189-93a43cff-d5541515-97932796.svg)
成熟代码通常处理过部分常见问题和边界情况，因此有机会减少重新实现和调试的成本。

但搜索和理解代码同样消耗 Token，复用并不保证每次都更省。

## 什么时候应该复用？

不是所有 GitHub 代码都值得采用。

需要考虑许可证、维护情况、安全性、兼容性和测试结果。如果功能非常简单，从零编写反而可能更划算。

推荐采用以下优先级：

![直接复用、修改实现、从零编写的优先级](/static/migrated/diagrams/plantuml/31eb2df9-2bec58b9-9b2642c7-f459961d-92f6eeff-1343378b-8fe64c6f-378e281a.svg)
## 总结

GitPilfer 的价值在于改变 AI 的编程习惯：先找成熟实现，再决定要不要写新代码。

实际节省多少 Token，还需要根据任务测试验证。

AI 编程不只是让代码生成得更快，也要尽量减少不必要的重复开发。

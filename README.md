# `ʕ•ᴥ•ʔ Bear Blog`

**A calm home for your writing.** Start a free blog in minutes at [bearblog.dev](https://bearblog.dev).

Simple, super-fast, with no trackers. A place where (human) words matter most.

- [Explore Bear Blog](https://bearblog.dev)
- [Read the documentation](https://docs.bearblog.dev)
- [Report a bug or request a feature](https://herman.bearblog.dev/contact/)
- [Contribution information](CONTRIBUTIONS.md)
- [个人博客内容存储、Git 同步与恢复](CONTENT.md)
- [通过 Tailscale 使用 MCP 管理文章和草稿](MCP.md)

## 通过 MCP 管理个人博客

个人博客模式支持通过 MCP 搜索文章、按标签筛选、管理独立页面，以及创建、局部更新、发布和撤回文章。隐藏文章就是将它转回草稿，正文和原链接地址不会被删除。MCP 客户端通过 Tailscale SSH 连接服务器上的管理命令，不需要额外开放 HTTP 端口。

文章中的 PlantUML 代码块会在服务器本地渲染为 PNG，存入网站的 SQLite 数据库后嵌入正文；Mermaid 代码块原样保存，由读者浏览器按需渲染。客户端配置、工具参数和隐藏文章的方法见 [MCP 使用指南](MCP.md)。

*Built and maintained by [Herman](https://herman.bearblog.dev)*
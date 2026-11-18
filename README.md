# `ʕ•ᴥ•ʔ Bear Blog`

**A calm home for your writing.** Start a free blog in minutes at [bearblog.dev](https://bearblog.dev).

Simple, super-fast, with no trackers. A place where (human) words matter most.

- [Explore Bear Blog](https://bearblog.dev)
- [Read the documentation](https://docs.bearblog.dev)
- [Report a bug or request a feature](https://herman.bearblog.dev/contact/)
- [Contribution information](CONTRIBUTIONS.md)
- [个人博客内容存储、Git 同步与恢复](CONTENT.md)
- [通过 Tailscale 使用 MCP 发布文章](MCP.md)

## 通过 MCP 发布文章

个人博客模式支持使用 MCP 创建、读取和更新文章，也可将草稿发布。MCP 客户端通过 Tailscale SSH 连接服务器上的管理命令，不需要额外开放 HTTP 端口；访问权限由 Tailscale SSH 策略和服务器账号控制。

文章中的 PlantUML 代码块会在服务器本地渲染为 PNG，上传到已配置的对象存储，再作为图片嵌入正文。部署需要安装 MCP 依赖；渲染图表还需要 Java、PlantUML jar 和对象存储。配置方法和客户端示例见 [MCP 发布指南](MCP.md)。

*Built and maintained by [Herman](https://herman.bearblog.dev)*
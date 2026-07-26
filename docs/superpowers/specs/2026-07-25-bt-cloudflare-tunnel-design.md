# 宝塔 Cloudflare Tunnel 开发助手：设计说明

## 目标

构建一个面向开发者的宝塔 Linux 面板应用。应用以一条 Cloudflare Tunnel 和用户指定的通配 DNS 记录，将没有固定公网 IP 的本机宝塔 Web 服务暴露给 Cloudflare；开发者以后只需在宝塔「网站」中创建站点或通配站点，不必在本应用中逐个绑定子域名。

## 已确认的产品边界

- 这是宝塔应用，不是独立 Web 服务或站点管理器。
- 安装后默认在宝塔首页展示，作为状态入口；设置页是完整操作页。
- 设置允许任意 Cloudflare 托管的左侧通配域名，例如 `*.dashen.wang`、`*.dev.dashen.wang` 或 `*.test.example.com`；不固定为 `*.dev.<域名>`。
- 应用不维护网站列表、不填写子域名、不管理每个站点的端口。
- Tunnel 只有一条通配入口，保留请求的 `Host` 头并送到本机宝塔 Web 服务。开发者在宝塔新建 `*.dev.dashen.wang` 或 `api.dev.dashen.wang` 等站点时，由宝塔 Web 服务器根据 Host 自动分流。
- 提供一键安装 `cloudflared` 和一键初始化；同时提供刷新状态、重启 Tunnel 服务。
- 应用只提醒安全风险，不自动替用户创建 Cloudflare Access、WAF 规则或防火墙规则。

## 方案选择

采用远程管理的 Cloudflare Tunnel。应用以用户提供的 API Token 调用 Cloudflare API：解析 Zone、创建/复用一条远程管理 Tunnel、写入通配 CNAME、写入一条通配 ingress 规则，并取得 Tunnel Token 用于本机 `cloudflared` 系统服务。该方式支持一键安装、可查询的健康状态和稳定的重启操作。

不采用只接受用户粘贴的 Tunnel Token：它要求用户提前在 Cloudflare 控制台创建 Tunnel、配置 public hostname 与 DNS，无法满足一键初始化和可靠状态诊断。也不采用逐子域名绑定：这会与通配 DNS 和宝塔 Host 自动分流重复。

Cloudflare 的远程管理 Tunnel 支持 API 创建、获取运行 Token 和读取连接状态；其 ingress 支持形如 `*.example.com` 的 hostname 规则。参考：

- https://developers.cloudflare.com/tunnel/setup/
- https://developers.cloudflare.com/tunnel/advanced/local-management/configuration-file/
- https://developers.cloudflare.com/dns/manage-dns-records/reference/wildcard-dns-records/

## 系统结构

```text
宝塔首页应用卡片 / 独立设置页
              │
              ▼
cf_tunnel_main.py（宝塔插件 API 边界）
              │
              ├── 配置存储：受限权限 JSON，不回传 Token 明文
              ├── Cloudflare API：Tunnel、DNS、连接健康
              └── 系统操作：检测/安装/重启 cloudflared
              │
              ▼
Cloudflare：*.用户测试域名 ── CNAME ── Tunnel
              │
              ▼
cloudflared 系统服务 ── 单条通配 ingress ── 本机宝塔 Web 服务
```

## 用户流程

1. 用户从宝塔首页的应用卡片打开设置。
2. 填写 Cloudflare 帐户 ID、API Token 与通配测试域名，例如 `*.dev.dashen.wang`。
3. 点击「保存设置」。
4. 点击「一键安装并配置」。
4. 应用验证域名格式和 Token，解析所属 Cloudflare Zone，安装 `cloudflared`，创建或复用 Tunnel，写入 Cloudflare 通配 DNS 与 ingress，并安装/启动系统服务。
5. 首页卡片和设置页显示安装、Tunnel、DNS 绑定、最近检查与安全提示。
6. 用户在宝塔「网站」中添加任意匹配的站点；应用无需再操作。

## 配置与安全

- API Token 仅写入插件私有配置文件，并设置为 `0600`；所有 API 响应、页面与日志均只显示掩码 Token。
- 配置页明确列出最小权限：目标 Zone 的 `DNS:Edit` 与 `Zone:Read`，所属账号的 `Cloudflare Tunnel:Edit`。
- Tunnel Token 仅用于注册本机 `cloudflared` 服务，不在页面或插件配置中保存/显示。
- 输入验证拒绝非通配、非 FQDN、含 URL/端口/空白字符的域名，防止命令注入。
- 系统命令固定为受控参数列表；用户输入绝不拼接到 shell 命令。
- 页面提示：不要把宝塔面板、数据库管理器或未授权管理端暴露到该通配域名；公网测试环境建议配置 Cloudflare Access，并收紧本机入站规则。

## 主页与设置页

首页卡片默认展示图标、名称、通配测试域名和四个状态：`cloudflared`、系统服务、Tunnel 连接、DNS 绑定；它提供「去配置 / 查看诊断 / 打开设置」的单个主动作。

设置页提供初次配置表单（帐户 ID、API Token、通配测试域名）、只保存设置的显式动作、一键安装并配置、刷新状态、重启服务、完整状态与安全提醒。动态文本必须通过 DOM 文本 API 渲染，绝不把 Cloudflare 响应当 HTML 插入。

## 错误处理与验收

- Cloudflare API 错误显示 Cloudflare 返回的可读消息；不展示 Authorization Header 或 Token。
- 不支持的 Linux 包管理器显示手工安装说明，且不会写入半成品配置。
- API Token 或域名验证失败时，不创建 Tunnel/DNS/系统服务。
- 创建后的任一步失败时保留清晰的失败阶段；不自动删除已有 Tunnel/DNS，以免删除用户资源。
- 单元测试覆盖通配域名解析、配置脱敏、Cloudflare 请求构造/错误转换、状态汇总和命令选择。
- 真实宝塔面板验收：导入插件后默认出现在首页，打开独立设置页，确认 Token 未泄露；只有用户另行提供测试 Cloudflare Token 时才改变 Cloudflare 资源。

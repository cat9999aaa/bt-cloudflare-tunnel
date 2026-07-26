# 宝塔 Cloudflare Tunnel 开发助手

一个面向开发者的宝塔 Linux 面板应用：通过一条 Cloudflare Tunnel 与一条通配 DNS 记录，将没有固定公网 IP 的本机宝塔网站用于测试。安装后默认出现在宝塔首页，并提供完整的独立设置页。

当前插件版本：`0.1.2`。版本号同时显示在宝塔「第三方应用」列表和插件设置页顶部。

> 这个插件不管理网站、不填写子域名、也不维护端口映射。通配域名配置完成后，开发者只在宝塔「网站」中新增站点，由宝塔 Web 服务按请求域名自动分流。

## 功能

- 默认在宝塔首页显示应用入口与简要健康状态。
- 独立设置页，保存 Cloudflare 帐户 ID、API Token 和任意左侧通配测试域名。
- 一键安装 `cloudflared`，创建远程管理 Tunnel，配置通配 ingress 和 Cloudflare DNS CNAME，并注册为系统服务。
- 状态诊断：`cloudflared` 版本、系统服务、Cloudflare Tunnel 是否有连接、DNS 是否仍正确绑定。
- 支持 `*.dashen.wang`、`*.dev.dashen.wang`、`*.test.example.com` 等任意由当前 Token 管理的通配域名。
- 提供安全防护提醒，不自动开放宝塔后台、数据库管理工具或其他管理端。

## 工作方式

```text
*.dev.dashen.wang
        │ Cloudflare 通配 DNS
        ▼
Cloudflare Tunnel
        ▼
本机 cloudflared 服务
        ▼
宝塔 Web 服务
        ▼
按 Host 头自动匹配宝塔网站
```

例如，插件配置 `*.dev.dashen.wang` 后：

- 在宝塔「网站」中新建 `api.dev.dashen.wang`，即可从 Cloudflare Tunnel 访问该网站。
- 也可创建 `*.dev.dashen.wang` 的通配网站，由宝塔处理任意匹配子域名。
- 插件不需要、也不会保存 `api`、`demo`、`admin` 等具体子域名。

## 前提条件

- 宝塔 Linux 面板，建议使用当前稳定版本。
- 域名的权威 DNS 已托管到 Cloudflare。
- 宝塔 Web 服务已运行，并可从本机 HTTP 入口处理网站请求。
- 服务器允许向 Cloudflare 发起出站连接；Cloudflare Tunnel 使用出站连接，不要求服务器具有固定公网 IP。
- 运行一键安装的面板进程需要具备安装软件包、注册 systemd 服务的权限。

## 创建最小权限 Cloudflare API Token

在 Cloudflare 创建仅供本插件使用的 API Token，并将资源范围限制到目标 Zone 与对应账号。

| 范围 | 权限 | 用途 |
|---|---|---|
| Zone | `DNS:Edit` | 创建或更新通配 CNAME |
| Zone | `Zone:Read` | 从输入域名识别所属 Zone |
| Account | `Cloudflare Tunnel:Edit` | 创建 Tunnel、写入 ingress、读取连接状态和获取运行 Token |

不要使用 Global API Key，也不要复用拥有全部账号权限的 Token。插件只会把 Token 写到宝塔本机私有配置文件，并将文件权限设为 `0600`；界面、状态响应和日志不会返回 Token 明文。

## 安装

1. 生成插件包：

   ```bash
   ./package-plugin.sh
   ```

2. 在宝塔面板打开「软件商店」→「第三方应用」→「导入插件」。
3. 上传 `dist/cf_tunnel.zip` 并安装。
4. 回到宝塔首页，默认显示的「Cloudflare Tunnel 开发助手」入口会出现；点击即可打开设置页。

开发调试时，也可以将 `cf_tunnel/` 目录复制到服务器的 `/www/server/panel/plugin/cf_tunnel/`，并在宝塔开发者模式中刷新页面。

## 首次配置

1. 打开插件设置页。
2. 输入 Cloudflare 帐户 ID（32 位十六进制字符串）。它可在 Cloudflare 帐户页面或 API Token 创建完成页找到。
3. 输入上表权限范围内的 Cloudflare API Token。
4. 输入通配测试域名，例如 `*.dev.dashen.wang` 或 `*.dashen.wang`。
5. 点击「保存设置」：此步骤只将设置以 `0600` 权限保存到宝塔本机，不会访问 Cloudflare、安装软件或改动 DNS。
6. 确认状态显示「已保存，等待配置」后，点击「一键安装并配置」。

插件会：

1. 校验通配域名格式，并确认帐户 ID 与 Token 能访问的 Zone 所属账号一致。
2. 使用 Cloudflare 官方软件源安装 `cloudflared`（apt、dnf、yum）。
3. 创建一条远程管理的 Cloudflare Tunnel。
4. 在 Tunnel 中配置这一条通配入口，并统一交给本机宝塔 Web 服务。
5. 创建或更新 `*.你的测试域名 → <Tunnel-ID>.cfargotunnel.com` 的 Cloudflare CNAME。
6. 注册并启动本机 `cloudflared` 系统服务。

配置完成后只需回到宝塔「网站」新建站点，无需到此插件新增绑定。

## 首页与状态含义

| 状态 | 含义 | 建议处理 |
|---|---|---|
| cloudflared 未安装 | 本机没有可运行的 Tunnel 客户端 | 在设置页运行一键安装 |
| 系统服务未运行 | `cloudflared` 服务未连接 | 使用「重启 Tunnel 服务」，再刷新状态 |
| Cloudflare Tunnel 待配置 | 尚未保存帐户 ID、Token 和通配域名；插件不会在此状态查询 Cloudflare | 先保存最小权限 Token 设置 |
| Cloudflare Tunnel 未连接 | Cloudflare 未看到活跃连接 | 检查服务器出站网络、Token 和 systemd 日志 |
| DNS 绑定未绑定 | 通配 CNAME 缺失、未代理或未指向当前 Tunnel | 检查 Cloudflare DNS，必要时重新配置 |
| 开发通道已就绪 | 本机服务、Tunnel 和 DNS 均处于健康状态 | 可直接在宝塔新增测试网站 |

## 安全防护

- 不要把宝塔后台、phpMyAdmin、数据库面板、SSH Web 终端或无鉴权管理端放在该通配测试域名下。
- 共享给他人测试时，在 Cloudflare 配置 Access 身份验证和访问策略。
- 将服务器入站防火墙收紧到必要服务；Tunnel 只需要向 Cloudflare 发起出站连接。
- 为插件创建独立、最小权限的 API Token；不用时立刻在 Cloudflare 撤销。
- 一键安装失败时不要反复粘贴高权限 Token 到终端。先查看状态提示、软件源和 systemd 日志。

## 故障排查

### 一键安装提示不支持包管理器

插件内置 apt、dnf、yum。其他发行版请按 [Cloudflare cloudflared 下载文档](https://developers.cloudflare.com/tunnel/downloads/) 手动安装后再刷新插件状态。

### Tunnel 未连接

检查服务：

```bash
systemctl status cloudflared
journalctl -u cloudflared -n 100 --no-pager
```

确认服务器允许出站访问 Cloudflare，并检查 Cloudflare Token 的 Tunnel 权限。

### 新建宝塔网站后仍无法访问

确认：

1. 站点域名与插件配置的通配域名匹配。
2. 插件的「DNS 绑定」与「Cloudflare Tunnel」均为健康状态。
3. 宝塔 Web 服务已运行，并能从本机处理对应 Host。
4. 未被 Cloudflare Access、WAF、站点防火墙或本机防火墙拦截。

## 卸载边界

卸载插件只移除宝塔入口图标与插件文件。为了避免误删生产外资源，插件不会自动删除 Cloudflare Tunnel、DNS 记录、`cloudflared` 软件包或已注册的系统服务；请在确认不再需要后手动清理。

## 开发与验证

```bash
uv run python -m pytest -q
./package-plugin.sh
unzip -l dist/cf_tunnel.zip
```

真实 Cloudflare 配置会创建外部资源。请使用测试 Zone 和专用 Token 进行验收，不要在未确认前使用生产域名或高权限凭据。

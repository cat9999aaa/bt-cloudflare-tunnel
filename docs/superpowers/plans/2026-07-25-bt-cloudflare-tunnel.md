# 宝塔 Cloudflare Tunnel 开发助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一个默认显示在宝塔首页、可一键安装并配置 Cloudflare Tunnel 通配域名的开发者插件。

**Architecture:** 插件使用宝塔标准的 Python 类 API 与静态设置页。后端将输入解析为受限领域对象，使用 Cloudflare HTTP API 管理单条远程 Tunnel/通配 DNS/ingress，使用固定系统命令检测、安装和重启 `cloudflared`，并把可公开展示的状态返回前端。

**Tech Stack:** 宝塔 Linux 面板第三方插件结构、Python 标准库、pytest、原生 HTML/CSS/JavaScript、Cloudflare v4 API、systemd、apt/dnf/yum。

## Global Constraints

- 插件目录名和后端类名均为 `cf_tunnel`；安装目标为 `/www/server/panel/plugin/cf_tunnel`。
- `info.json` 必须设置 `display: 1` 与 `default: true`，并提供独立的 `index.html` 设置页。
- 设置字段只允许 API Token 与左侧通配 FQDN；不提供站点、子域名或端口绑定表单。
- 所有 Tunnel 流量使用单条通配 ingress，转发到宝塔本机 HTTP 入口；不暴露逐站点转发表。
- API Token 绝不出现在响应、日志、README 示例或 Git 历史；本机配置文件权限为 `0600`。
- Linux 命令只通过固定参数列表执行；不把用户输入拼入 shell。
- 支持 apt、dnf、yum；未知包管理器只返回手动指引。
- README 必须以中文说明安装、Token 权限、配置、宝塔站点用法、状态含义、故障排查和安全防护。

---

### Task 1: 建立插件骨架与输入契约

**Files:**

- Create: `pyproject.toml`
- Create: `cf_tunnel/info.json`
- Create: `cf_tunnel/__init__.py`
- Create: `cf_tunnel/domain.py`
- Create: `cf_tunnel/storage.py`
- Create: `cf_tunnel/cf_tunnel_main.py`
- Create: `tests/test_domain.py`
- Create: `tests/test_manifest.py`

**Interfaces:**

- Consumes: 宝塔前端传入的 `token` 与 `wildcard_domain` 字符串。
- Produces: `PluginConfig`、`WildcardDomain`、`PublicStatus` 与 `{status, msg, data}` 响应。

- [ ] **Step 1: 写失败测试**

```python
def test_parse_wildcard_domain_accepts_a_deep_subdomain() -> None:
    assert parse_wildcard_domain("*.dev.dashen.wang").value == "*.dev.dashen.wang"

def test_manifest_enables_homepage_display() -> None:
    assert manifest["display"] == 1
```

- [ ] **Step 2: 确认 RED**

Run: `uv run python -m pytest tests/test_domain.py tests/test_manifest.py -q`

Expected: FAIL，因为模块和清单尚不存在。

- [ ] **Step 3: 最小实现**

```python
@dataclass(frozen=True, slots=True)
class WildcardDomain:
    value: str
    hostname: str

def parse_wildcard_domain(raw: str) -> WildcardDomain:
    value = raw.strip().lower()
    if value != raw or not value.startswith("*."):
        raise ValueError("请输入 *.example.com 形式的通配域名")
    hostname = value[2:]
    labels = hostname.split(".")
    if len(labels) < 2 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
        raise ValueError("请输入有效的通配 FQDN")
    return WildcardDomain(value=value, hostname=hostname)
```

清单使用：

```json
{"name":"cf_tunnel", "display":1, "default":true}
```

- [ ] **Step 4: 确认 GREEN**

Run: `uv run python -m pytest tests/test_domain.py tests/test_manifest.py -q`

Expected: PASS。

### Task 2: Cloudflare API 与配置流程

**Files:**

- Create: `cf_tunnel/cloudflare_api.py`
- Modify: `cf_tunnel/cf_tunnel_main.py`
- Modify: `cf_tunnel/storage.py`
- Create: `tests/test_cloudflare_api.py`
- Create: `tests/test_configuration_flow.py`

**Interfaces:**

- Consumes: `PluginConfig`。
- Produces: `TunnelDetails`、`DnsBinding` 和失败阶段明确的配置结果。

- [ ] **Step 1: 写失败测试**

```python
def test_configure_uses_wildcard_ingress_and_cname() -> None:
    result = service.configure(config)
    assert result.ingress_hostname == "*.dev.dashen.wang"
    assert result.dns_target.endswith(".cfargotunnel.com")
```

- [ ] **Step 2: 确认 RED**

Run: `uv run python -m pytest tests/test_cloudflare_api.py tests/test_configuration_flow.py -q`

Expected: FAIL，因为 `CloudflareClient` 尚不存在。

- [ ] **Step 3: 最小实现**

```python
class CloudflareClient:
    def resolve_zone(self, wildcard: WildcardDomain) -> Zone:
        for index in range(len(wildcard.hostname.split(".")) - 1):
            candidate = ".".join(wildcard.hostname.split(".")[index:])
            response = self.request("GET", "/zones?name=" + candidate)
            if response["result"]:
                return Zone.from_api(response["result"][0])
        raise CloudflareError("找不到由当前 Token 管理的 Cloudflare Zone")

    def create_tunnel(self, zone: Zone, name: str) -> TunnelDetails:
        response = self.request("POST", "/accounts/" + zone.account_id + "/cfd_tunnel", {"name": name, "config_src": "cloudflare"})
        return TunnelDetails.from_api(response["result"])

    def put_ingress(self, tunnel: TunnelDetails, wildcard: WildcardDomain) -> None:
        self.request("PUT", "/accounts/" + tunnel.account_id + "/cfd_tunnel/" + tunnel.id + "/configurations", {"config": {"ingress": [{"hostname": wildcard.value, "service": "http://127.0.0.1:80", "originRequest": {}}, {"service": "http_status:404"}]}})

    def upsert_wildcard_cname(self, zone: Zone, tunnel: TunnelDetails, wildcard: WildcardDomain) -> DnsBinding:
        return self.create_or_update_cname(zone, wildcard, tunnel.id + ".cfargotunnel.com")
```

`put_ingress` 写入 `hostname: <用户通配域名>` → `service: http://127.0.0.1:80`，并以 `http_status:404` 兜底。所有 HTTP 错误转换为不含 Token 的可读消息。

- [ ] **Step 4: 确认 GREEN**

Run: `uv run python -m pytest tests/test_cloudflare_api.py tests/test_configuration_flow.py -q`

Expected: PASS。

### Task 3: cloudflared 一键安装、服务控制与状态

**Files:**

- Create: `cf_tunnel/system_service.py`
- Modify: `cf_tunnel/cf_tunnel_main.py`
- Create: `tests/test_system_service.py`
- Create: `tests/test_status.py`

**Interfaces:**

- Consumes: `TunnelDetails.token`、运行环境中的包管理器和 systemd 状态。
- Produces: `CloudflaredStatus(installed, version, service_active, detail)` 和安全的用户动作响应。

- [ ] **Step 1: 写失败测试**

```python
def test_apt_installer_uses_official_repository() -> None:
    plan = installer.plan_for("apt")
    assert "pkg.cloudflare.com" in plan.steps[0]
    assert "cloudflared" in plan.steps[-1]
```

- [ ] **Step 2: 确认 RED**

Run: `uv run python -m pytest tests/test_system_service.py tests/test_status.py -q`

Expected: FAIL，因为系统服务层尚不存在。

- [ ] **Step 3: 最小实现**

```python
class CloudflaredSystem:
    def install_package(self) -> OperationResult:
        return self.run_plan(self.plan_for(self.detect_package_manager()))

    def install_service(self, tunnel_token: str) -> OperationResult:
        return self.run(["cloudflared", "service", "install", tunnel_token])

    def restart_service(self) -> OperationResult:
        return self.run(["systemctl", "restart", "cloudflared"])

    def inspect(self) -> CloudflaredStatus:
        return CloudflaredStatus.from_commands(self.run(["cloudflared", "--version"]), self.run(["systemctl", "is-active", "cloudflared"]))
```

支持 apt、dnf、yum 的官方仓库命令；用 `subprocess.run(command, shell=False)` 执行固定参数。配置流在 cloudflared 安装后再调用 `cloudflared service install <token>`。

- [ ] **Step 4: 确认 GREEN**

Run: `uv run python -m pytest tests/test_system_service.py tests/test_status.py -q`

Expected: PASS。

### Task 4: 首页默认入口与独立设置页

**Files:**

- Create: `DESIGN.md`
- Create: `cf_tunnel/index.html`
- Create: `cf_tunnel/static/cf-tunnel.css`
- Create: `cf_tunnel/static/cf-tunnel.js`
- Create: `tests/test_frontend_contract.py`

**Interfaces:**

- Consumes: `get_status`、`configure`、`restart_service` 插件 API。
- Produces: 默认首页入口、设置页、状态展示与安全提示。

- [ ] **Step 1: 写失败测试**

```python
def test_settings_page_exposes_setup_and_security_actions() -> None:
    html = Path("cf_tunnel/index.html").read_text()
    assert "一键安装并配置" in html
    assert "安全防护" in html
    assert "get_status" in html
```

- [ ] **Step 2: 确认 RED**

Run: `uv run python -m pytest tests/test_frontend_contract.py -q`

Expected: FAIL，因为设置页尚不存在。

- [ ] **Step 3: 最小实现**

页面采用宝塔已有的 jQuery/layer 请求模式，不引入打包工具。表单只含 Token 与通配域名；所有动态文本通过 DOM `text()` 写入。

- [ ] **Step 4: 确认 GREEN 与视觉 QA**

Run: `uv run python -m pytest tests/test_frontend_contract.py -q`

Expected: PASS；随后在宝塔面板验证首页默认展示、未配置/异常/健康状态与窄屏布局。

### Task 5: 打包、README、真实面板验收与公开发布

**Files:**

- Create: `README.md`
- Create: `package-plugin.sh`
- Create: `.gitignore`
- Create: `cf_tunnel/install.sh`
- Create: `tests/test_package.py`

**Interfaces:**

- Consumes: 完整 `cf_tunnel/` 目录。
- Produces: 可导入宝塔的 `dist/cf_tunnel.zip` 和公开开发者文档。

- [ ] **Step 1: 写失败测试**

```python
def test_plugin_archive_excludes_tests_and_secrets() -> None:
    names = package_names()
    assert "cf_tunnel/info.json" in names
    assert all("token" not in name.lower() for name in names)
```

- [ ] **Step 2: 确认 RED**

Run: `uv run python -m pytest tests/test_package.py -q`

Expected: FAIL，因为打包脚本尚不存在。

- [ ] **Step 3: 最小实现**

README 以中文覆盖功能、系统前提、导入/升级、Token 权限、通配域名示例、宝塔网站用法、首页状态、故障排查与安全防护。打包脚本生成 ZIP 并排除测试、缓存、配置、密钥和 Git 文件。

- [ ] **Step 4: 全量验证与手工验收**

Run: `uv run python -m pytest -q && ./package-plugin.sh && unzip -l dist/cf_tunnel.zip`

Expected: 全部测试通过，ZIP 包含 `cf_tunnel/info.json`、`index.html`、后端代码和静态资源。导入用户提供的宝塔面板，确认首页默认展示、设置页可打开、Token 未泄露。没有测试 Cloudflare Token 时不得改变 Cloudflare 资源。

- [ ] **Step 5: 发布公开 GitHub 仓库**

```bash
gh repo create bt-cloudflare-tunnel --public --source=. --remote=origin --push
```

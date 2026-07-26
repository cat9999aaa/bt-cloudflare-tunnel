from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable, Tuple

try:
    from .compat import frozen_dataclass
    from .cloudflare_api import (
        CloudflareApiError,
        CloudflareClient,
        ConfigurationResult,
        RemoteStatus,
    )
    from .configuration import ConfigurationService
    from .domain import (
        DomainValidationError,
        PluginConfig,
        parse_cloudflare_account_id,
        parse_wildcard_domain,
    )
    from .storage import ConfigStore
    from .system_service import CloudflaredStatus, CloudflaredSystem, OperationResult
except ImportError:
    from compat import frozen_dataclass
    from cloudflare_api import (
        CloudflareApiError,
        CloudflareClient,
        ConfigurationResult,
        RemoteStatus,
    )
    from configuration import ConfigurationService
    from domain import (
        DomainValidationError,
        PluginConfig,
        parse_cloudflare_account_id,
        parse_wildcard_domain,
    )
    from storage import ConfigStore
    from system_service import CloudflaredStatus, CloudflaredSystem, OperationResult


Setup = Callable[[PluginConfig], Tuple[ConfigurationResult, str]]
RemoteStatusReader = Callable[[PluginConfig], RemoteStatus]


class SystemOperations:
    def install_package(self) -> OperationResult: ...

    def install_service(self, tunnel_token: str) -> OperationResult: ...

    def restart_service(self) -> OperationResult: ...

    def inspect(self) -> CloudflaredStatus: ...


@frozen_dataclass
class PluginDependencies:
    store: ConfigStore
    system: SystemOperations
    setup: Setup
    remote_status: RemoteStatusReader


class cf_tunnel_main:
    """Baota plugin endpoint class for Cloudflare Tunnel operations."""

    def __init__(self, dependencies: PluginDependencies | None = None) -> None:
        active = dependencies or self._default_dependencies()
        self._store = active.store
        self._system = active.system
        self._setup = active.setup
        self._remote_status = active.remote_status

    def get_status(self, _args: object) -> dict[str, object]:
        config = self._store.load()
        cloudflared = self._system.inspect()
        remote = self._read_remote_status(config)
        settings_saved = config is not None and config.account_id is not None
        configured = self._is_configured(config)
        return {
            "status": True,
            "msg": "状态获取成功",
            "data": {
                "settings_saved": settings_saved,
                "configured": configured,
                "wildcard_domain": config.wildcard.value if config is not None else "",
                "account_id": (
                    config.account_id.value
                    if config is not None and config.account_id is not None
                    else ""
                ),
                "cloudflared_installed": cloudflared.installed,
                "cloudflared_version": cloudflared.version,
                "service_active": cloudflared.service_active,
                "tunnel_connected": remote.tunnel_connected,
                "dns_bound": remote.dns_bound,
            },
        }

    def save_settings(self, args: object) -> dict[str, object]:
        token = getattr(args, "token", "")
        raw_account_id = getattr(args, "account_id", "")
        raw_domain = getattr(args, "wildcard_domain", "")
        if not isinstance(token, str) or not token.strip():
            return self._failure("请填写 Cloudflare API Token")
        if not isinstance(raw_account_id, str):
            return self._failure("请填写 Cloudflare 帐户 ID")
        if not isinstance(raw_domain, str):
            return self._failure("请填写通配测试域名")

        try:
            account_id = parse_cloudflare_account_id(raw_account_id)
            config = PluginConfig(
                token=token.strip(),
                wildcard=parse_wildcard_domain(raw_domain),
                account_id=account_id,
            )
            existing = self._store.load()
            if (
                existing is not None
                and existing.account_id == config.account_id
                and existing.wildcard == config.wildcard
            ):
                config = replace(existing, token=config.token)
            self._store.save(config)
        except DomainValidationError as error:
            return self._failure(str(error))

        return {
            "status": True,
            "msg": "设置已保存，可开始一键配置",
            "data": {
                "wildcard_domain": config.wildcard.value,
                "account_id": account_id.value,
            },
        }

    def configure(self, _args: object) -> dict[str, object]:
        config = self._store.load()
        account_id = config.account_id if config is not None else None
        if config is None or account_id is None:
            return self._failure("请先保存帐户 ID、API Token 和通配测试域名")

        try:
            installation = self._system.install_package()
            if not installation.success:
                return self._failure(installation.message)
            result, tunnel_token = self._setup(config)
            saved_config = replace(
                config,
                zone_id=result.zone.id,
                tunnel_id=result.tunnel.id,
                tunnel_name=result.tunnel.name,
                dns_target=result.dns_binding.target,
            )
            self._store.save(saved_config)
            service = self._system.install_service(tunnel_token)
            if not service.success:
                return self._failure(service.message)
        except CloudflareApiError as error:
            return self._failure(str(error))

        return {
            "status": True,
            "msg": "Cloudflare Tunnel 配置完成",
            "data": {
                "wildcard_domain": config.wildcard.value,
                "tunnel_id": result.tunnel.id,
                "dns_target": result.dns_binding.target,
            },
        }

    def restart_service(self, _args: object) -> dict[str, object]:
        result = self._system.restart_service()
        if result.success:
            return {"status": True, "msg": result.message, "data": {}}
        return self._failure(result.message)

    @staticmethod
    def _configure_cloudflare(config: PluginConfig) -> tuple[ConfigurationResult, str]:
        client = CloudflareClient(config.token)
        result = ConfigurationService(client).configure(config)
        return result, client.get_tunnel_token(result.tunnel)

    @staticmethod
    def _get_remote_status(config: PluginConfig) -> RemoteStatus:
        if (
            config.zone_id is None
            or config.account_id is None
            or config.tunnel_id is None
            or config.tunnel_name is None
        ):
            return RemoteStatus(tunnel_connected=False, dns_bound=False)
        client = CloudflareClient(config.token)
        tunnel = client.tunnel_from_values(
            config.tunnel_id, config.tunnel_name, config.account_id.value
        )
        return client.get_remote_status(tunnel, config.zone_id, config.wildcard)

    @classmethod
    def _default_dependencies(cls) -> PluginDependencies:
        return PluginDependencies(
            store=ConfigStore(Path("/www/server/panel/data/cf_tunnel/config.json")),
            system=CloudflaredSystem(),
            setup=cls._configure_cloudflare,
            remote_status=cls._get_remote_status,
        )

    def _read_remote_status(self, config: PluginConfig | None) -> RemoteStatus:
        if config is None:
            return RemoteStatus(tunnel_connected=False, dns_bound=False)
        try:
            return self._remote_status(config)
        except CloudflareApiError:
            return RemoteStatus(tunnel_connected=False, dns_bound=False)

    @staticmethod
    def _is_configured(config: PluginConfig | None) -> bool:
        return (
            config is not None
            and config.zone_id is not None
            and config.tunnel_id is not None
            and config.tunnel_name is not None
        )

    @staticmethod
    def _failure(message: str) -> dict[str, object]:
        return {"status": False, "msg": message, "data": {}}

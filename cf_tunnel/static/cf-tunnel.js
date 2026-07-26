(function () {
  "use strict";

  if (typeof window.jQuery !== "function") {
    return;
  }

  var pluginName = "cf_tunnel";
  var savedSettings = false;
  var selectors = {
    accountId: "#cf-tunnel-account-id",
    binary: "#cf-tunnel-binary",
    configure: "#cf-tunnel-configure",
    dnsBinding: "#cf-tunnel-dns-binding",
    dnsDetail: "#cf-tunnel-dns-detail",
    domain: "#cf-tunnel-domain",
    feedback: "#cf-tunnel-feedback",
    overall: "#cf-tunnel-overall",
    save: "#cf-tunnel-save",
    service: "#cf-tunnel-service",
    settings: "#cf-tunnel-settings",
    token: "#cf-tunnel-token",
    tunnel: "#cf-tunnel-tunnel",
    version: "#cf-tunnel-version"
  };

  function requestPlugin(action, payload, callback, onError) {
    if (typeof window.request_plugin !== "function") {
      onError("此页面必须从宝塔面板打开；本地预览不连接插件接口。");
      return;
    }
    window.request_plugin(pluginName, action, payload, callback, 3600000);
  }

  function setFeedback(message, state) {
    $(selectors.feedback).text(message).attr("data-state", state || "");
  }

  function setOverall(text, state) {
    $(selectors.overall)
      .text(text)
      .removeClass("cf-tunnel__chip--neutral cf-tunnel__chip--healthy cf-tunnel__chip--warning cf-tunnel__chip--error")
      .addClass("cf-tunnel__chip--" + state);
  }

  function setStatus(data) {
    var settingsSaved = data.settings_saved === true;
    var configured = data.configured === true;
    var installed = data.cloudflared_installed === true;
    var active = data.service_active === true;
    var tunnelConnected = data.tunnel_connected === true;
    var dnsBound = data.dns_bound === true;

    savedSettings = settingsSaved;
    $(selectors.settings).text(settingsSaved ? (configured ? "已保存并已配置" : "已保存，等待配置") : "尚未保存");
    $(selectors.configure).prop("disabled", !settingsSaved);
    $(selectors.binary).text(installed ? "已安装" : "未安装");
    $(selectors.version).text(installed && data.cloudflared_version ? data.cloudflared_version : "等待一键安装");
    $(selectors.service).text(active ? "运行中" : "未运行");
    $(selectors.tunnel).text(tunnelConnected ? "已连接" : "未连接");
    $(selectors.dnsBinding).text(dnsBound ? "已绑定" : "未绑定");
    $(selectors.dnsDetail).text(configured ? data.wildcard_domain : "先保存设置并完成配置");
    $(selectors.accountId).val(data.account_id || "");
    $(selectors.domain).val(data.wildcard_domain || "");

    if (configured && installed && active && tunnelConnected && dnsBound) {
      setOverall("开发通道已就绪", "healthy");
      return;
    }
    if (settingsSaved) {
      setOverall(configured ? "需要检查服务" : "等待一键配置", "warning");
      return;
    }
    setOverall("等待保存设置", "neutral");
  }

  function refreshStatus() {
    requestPlugin("get_status", {}, function (response) {
      if (response.status) {
        setStatus(response.data);
        return;
      }
      setFeedback(response.msg, "error");
      setOverall("状态检查失败", "error");
    }, function (message) {
      setFeedback(message, "error");
      setOverall("未连接宝塔", "error");
    });
  }

  function settingsPayload() {
    return {
      account_id: $(selectors.accountId).val(),
      token: $(selectors.token).val(),
      wildcard_domain: $(selectors.domain).val()
    };
  }

  function hasSettings(payload) {
    if (payload.account_id && payload.token && payload.wildcard_domain) {
      return true;
    }
    setFeedback("请填写 Cloudflare 帐户 ID、API Token 和通配测试域名。", "error");
    return false;
  }

  function saveSettings(event) {
    event.preventDefault();
    var payload = settingsPayload();
    if (!hasSettings(payload)) {
      return;
    }
    $(selectors.save).prop("disabled", true).text("正在保存");
    setFeedback("正在保存设置。", "");
    function restoreSubmit() {
      $(selectors.save).prop("disabled", false).text("保存设置");
    }
    requestPlugin("save_settings", payload, function (response) {
      restoreSubmit();
      if (response.status) {
        $(selectors.token).val("");
        setFeedback(response.msg, "success");
        refreshStatus();
        return;
      }
      setFeedback(response.msg, "error");
    }, function (message) {
      restoreSubmit();
      setFeedback(message, "error");
    });
  }

  function configure() {
    if (!savedSettings) {
      setFeedback("请先保存 Cloudflare 帐户 ID、API Token 和通配测试域名。", "error");
      return;
    }
    $(selectors.configure).prop("disabled", true).text("正在安装并配置");
    setFeedback("正在执行，请勿关闭此窗口。", "");
    function restoreConfigure() {
      $(selectors.configure).prop("disabled", false).text("一键安装并配置");
    }
    requestPlugin("configure", {}, function (response) {
      restoreConfigure();
      if (response.status) {
        setFeedback(response.msg, "success");
        refreshStatus();
        return;
      }
      setFeedback(response.msg, "error");
    }, function (message) {
      restoreConfigure();
      setFeedback(message, "error");
    });
  }

  function restartService() {
    requestPlugin("restart_service", {}, function (response) {
      setFeedback(response.msg, response.status ? "success" : "error");
      if (response.status) {
        refreshStatus();
      }
    }, function (message) {
      setFeedback(message, "error");
    });
  }

  $("#cf-tunnel-setup").on("submit", saveSettings);
  $(selectors.configure).on("click", configure);
  $("#cf-tunnel-refresh").on("click", refreshStatus);
  $("#cf-tunnel-restart").on("click", restartService);
  refreshStatus();
}());

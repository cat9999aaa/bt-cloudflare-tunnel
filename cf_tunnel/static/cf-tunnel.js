(function () {
  "use strict";

  var pluginName = "cf_tunnel";
  var selectors = {
    binary: "#cf-tunnel-binary",
    domain: "#cf-tunnel-dns-binding",
    dnsDetail: "#cf-tunnel-dns-detail",
    feedback: "#cf-tunnel-feedback",
    overall: "#cf-tunnel-overall",
    service: "#cf-tunnel-service",
    submit: "#cf-tunnel-submit",
    tunnel: "#cf-tunnel-tunnel",
    version: "#cf-tunnel-version"
  };

  function requestPlugin(action, payload, callback, onError) {
    $.ajax({
      type: "POST",
      url: "/plugin?action=a&s=" + action + "&name=" + pluginName,
      data: payload,
      timeout: 3600000,
      success: callback,
      error: function () {
        setFeedback("无法连接宝塔插件接口，请刷新页面后重试。", "error");
        if (onError) {
          onError();
        }
      }
    });
  }

  function setFeedback(message, state) {
    $(selectors.feedback).text(message).attr("data-state", state || "");
  }

  function setOverall(text, state) {
    $(selectors.overall).text(text).removeClass("cf-tunnel__chip--neutral cf-tunnel__chip--healthy cf-tunnel__chip--warning cf-tunnel__chip--error").addClass("cf-tunnel__chip--" + state);
  }

  function setStatus(data) {
    var configured = data.configured === true;
    var installed = data.cloudflared_installed === true;
    var active = data.service_active === true;
    var tunnelConnected = data.tunnel_connected === true;
    var dnsBound = data.dns_bound === true;
    $(selectors.binary).text(installed ? "已安装" : "未安装");
    $(selectors.version).text(installed && data.cloudflared_version ? data.cloudflared_version : "等待一键安装");
    $(selectors.service).text(active ? "运行中" : "未运行");
    $(selectors.tunnel).text(tunnelConnected ? "已连接" : "未连接");
    $(selectors.domain).text(dnsBound ? "已绑定" : "未绑定");
    $(selectors.dnsDetail).text(configured ? data.wildcard_domain : "先完成首次配置");
    if (configured && installed && active && tunnelConnected && dnsBound) {
      setOverall("开发通道已就绪", "healthy");
      return;
    }
    if (configured) {
      setOverall("需要检查服务", "warning");
      return;
    }
    setOverall("等待首次配置", "neutral");
  }

  function refreshStatus() {
    requestPlugin("get_status", {}, function (response) {
      if (response.status) {
        setStatus(response.data);
        return;
      }
      setFeedback(response.msg, "error");
      setOverall("状态检查失败", "error");
    });
  }

  function configure(event) {
    event.preventDefault();
    var token = $("#cf-tunnel-token").val();
    var wildcardDomain = $("#cf-tunnel-domain").val();
    if (!token || !wildcardDomain) {
      setFeedback("请先填写 Cloudflare API Token 和通配测试域名。", "error");
      return;
    }
    $(selectors.submit).prop("disabled", true).text("正在安装并配置");
    setFeedback("正在执行，请勿关闭此窗口。", "");
    function restoreSubmit() {
      $(selectors.submit).prop("disabled", false).text("一键安装并配置");
    }
    requestPlugin("configure", { token: token, wildcard_domain: wildcardDomain }, function (response) {
      restoreSubmit();
      if (response.status) {
        $("#cf-tunnel-token").val("");
        setFeedback(response.msg, "success");
        refreshStatus();
        return;
      }
      setFeedback(response.msg, "error");
    }, restoreSubmit);
  }

  function restartService() {
    requestPlugin("restart_service", {}, function (response) {
      setFeedback(response.msg, response.status ? "success" : "error");
      if (response.status) {
        refreshStatus();
      }
    });
  }

  $("#cf-tunnel-setup").on("submit", configure);
  $("#cf-tunnel-refresh").on("click", refreshStatus);
  $("#cf-tunnel-restart").on("click", restartService);
  refreshStatus();
}());

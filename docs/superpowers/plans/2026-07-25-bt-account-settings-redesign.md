# Account Settings and BaoTa Transport Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable Account ID/API Token/wildcard settings, configure only from saved settings, and make the page use BaoTa's plugin transport while replacing the card-heavy settings page with the documented configuration-ledger layout.

**Architecture:** `domain.py` parses a 32-character Cloudflare Account ID with the wildcard domain into `PluginConfig`; `cf_tunnel_main.py` owns save/configure lifecycle and exposes `settings_saved` independently from remote health. `configuration.py` owns Tunnel orchestration and validates that the selected Zone belongs to the saved account. The browser page delegates requests to BaoTa's `request_plugin` helper when available and uses an explicit fallback only for hosts that do not supply it.

**Tech Stack:** Python 3.11 stdlib, pytest, vanilla HTML/CSS/JavaScript, BaoTa plugin API, Cloudflare v4 API.

## Global Constraints

- Do not persist, print, return or commit API Tokens outside the private `0600` configuration file.
- Settings save performs no Cloudflare, package-manager or systemd operation.
- Tunnel configuration requires previously saved settings and validates Zone/account identity before any Tunnel mutation.
- Preserve wildcard-only routing; no per-site domain or port form is introduced.
- Use BaoTa's `request_plugin` host helper when present; retain an error callback and button restoration for failed calls.
- Follow the updated `DESIGN.md`; controls remain keyboard-accessible with 44px minimum targets.

---

### Task 1: Persist validated account settings

**Files:**
- Modify: `cf_tunnel/domain.py`, `cf_tunnel/storage.py`, `cf_tunnel/cf_tunnel_main.py`
- Test: `tests/test_domain.py`, `tests/test_storage.py`, `tests/test_plugin_api.py`

- [ ] Write failing tests for a valid Account ID, an invalid Account ID, `save_settings`, private persistence and `settings_saved` status.
- [ ] Run `uv run python -m pytest tests/test_domain.py tests/test_storage.py tests/test_plugin_api.py -q` and confirm the new tests fail.
- [ ] Add Account ID parsing, persist it with the token/wildcard, preserve a matching remote configuration and clear one whose account/domain changed.
- [ ] Make `configure` load saved settings instead of accepting credentials from request arguments.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Validate the account in Cloudflare orchestration

**Files:**
- Create: `cf_tunnel/configuration.py`
- Modify: `cf_tunnel/cloudflare_api.py`, `cf_tunnel/cf_tunnel_main.py`
- Test: `tests/test_configuration_flow.py`, `tests/test_cloudflare_api.py`

- [ ] Write a failing configuration-flow test where the Zone account differs from the saved Account ID.
- [ ] Run `uv run python -m pytest tests/test_configuration_flow.py tests/test_cloudflare_api.py -q` and confirm it fails.
- [ ] Extract `ConfigurationService` to `configuration.py`; require a matching account before creating or reusing a Tunnel.
- [ ] Re-run focused tests and strict type checks.

### Task 3: Rebuild the settings interaction and layout

**Files:**
- Modify: `cf_tunnel/index.html`, `cf_tunnel/static/cf-tunnel.js`, `cf_tunnel/static/cf-tunnel.css`, `DESIGN.md`
- Test: `tests/test_frontend_contract.py`

- [ ] Write failing contract tests for Account ID, Save Settings, saved-settings status, and BaoTa transport delegation.
- [ ] Run `uv run python -m pytest tests/test_frontend_contract.py -q` and confirm the tests fail.
- [ ] Implement the configuration-ledger layout, save/configure actions and `request_plugin` transport with safe request failure recovery.
- [ ] Re-run the contract tests, JavaScript syntax check and rendered desktop/mobile preview.

### Task 4: Package, verify and publish

**Files:**
- Modify: `README.md`, `docs/superpowers/specs/2026-07-25-bt-cloudflare-tunnel-design.md`
- Test: all tests and package test

- [ ] Document Account ID, save-first flow and BaoTa-host-only interface behavior without including credentials.
- [ ] Run full pytest, ruff, basedpyright, package verification and direct plugin import.
- [ ] Run visual QA on desktop and mobile states, then publish the reviewed commit.

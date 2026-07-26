# Cloudflare Tunnel 开发助手 Design System

## 0. Research Log

- Embedded refs: shortlisted GitHub Primer, Atlassian and Linear → picked `taste-skill` + Linear as the operational developer-tool reference; only its restrained status density, technical metadata and subtle surface hierarchy are adapted, with no copied brand assets or layout.
- UI pattern lookup: searched `developer settings status dashboard` in UI Pro Max → selected a compact status-first monitoring pattern: neutral chrome, explicit state text and one clear recovery action.
- Lazyweb: 2 desktop queries, 2 screens viewed (`/tmp/lazyweb-developer-status.png`, `/tmp/lazyweb-tunnel-dashboard.png`) → adopted the grammar of an immediate overall state, a compact status grid, last-check metadata and progressively disclosed setup details; no external screen is copied or committed.
- Imagen drafts: skipped — this is a native BaoTa admin surface with no bitmap/hero asset requirement; code-native SVG status iconography is more legible, lighter and aligned with the host panel.

## 1. Atmosphere & Identity

Reading this as: an operational developer settings screen embedded in BaoTa for a technical administrator, with a calm, trustworthy control-panel language. The redesign uses a compact **configuration ledger**: a single coherent settings surface, a small live-status rail and explicit save/configure phases. The signature is a quiet blue-to-amber route marker only in the header; the interface avoids a marketing-style hero and repeated floating cards. Design variance 3, motion intensity 2, visual density 7.

## 2. Color

| Role | Token | Value | Usage |
|---|---|---|---|
| Canvas | `--cf-canvas` | `#f5f7fb` | Settings-page background |
| Surface | `--cf-surface` | `#ffffff` | Cards, form panel |
| Surface muted | `--cf-surface-muted` | `#f8fafc` | Status rows, empty state |
| Text primary | `--cf-text` | `#172033` | Titles and values |
| Text secondary | `--cf-text-muted` | `#667085` | Explanations and metadata |
| Border | `--cf-border` | `#d9e1ee` | Form and card separators |
| Focus / primary | `--cf-primary` | `#2563eb` | Primary CTA and focus ring |
| Primary hover | `--cf-primary-hover` | `#1d4ed8` | CTA hover |
| Route amber | `--cf-route` | `#f59e0b` | Non-interactive connection accent only |
| Success | `--cf-success` | `#15803d` | Healthy state plus text |
| Success background | `--cf-success-bg` | `#ecfdf3` | Healthy status chip |
| Warning | `--cf-warning` | `#b54708` | Safety and incomplete status text |
| Warning background | `--cf-warning-bg` | `#fffaeb` | Safety notice |
| Warning border | `--cf-warning-border` | `#fedf89` | Safety notice boundary |
| Error | `--cf-danger` | `#b42318` | Error state text |
| Error background | `--cf-danger-bg` | `#fef3f2` | Error message background |

Color communicates status only together with a text label and icon. The route amber is never used as a CTA.

## 3. Typography

| Level | Size | Weight | Line-height | Usage |
|---|---:|---:|---:|---|
| Page title | 24px | 650 | 1.25 | Plugin title |
| Section title | 18px | 650 | 1.35 | Card headings |
| Card title | 16px | 600 | 1.4 | Status item labels |
| Body | 14px | 400 | 1.6 | Help and safety copy |
| Label | 13px | 600 | 1.4 | Form labels and state labels |
| Metadata | 12px | 500 | 1.4 | Version, IDs and timestamps |

- Primary stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif`.
- Technical values: `ui-monospace, SFMono-Regular, Consolas, monospace`.
- Body text never falls below 14px; metadata must always have a visible adjacent label.

## 4. Spacing & Layout

Base unit: 4px. Tokens: `--cf-space-1: 4px`, `--cf-space-2: 8px`, `--cf-space-3: 12px`, `--cf-space-4: 16px`, `--cf-space-5: 20px`, `--cf-space-6: 24px`, `--cf-space-8: 32px`.

- Content uses a `stack` primitive with 24px section gaps and 16px card gaps.
- The status grid uses `repeat(auto-fit, minmax(min(13rem, 100%), 1fr))`, preventing a horizontal scroll on narrow panels.
- The form/safety region uses a `sidebar` primitive on wide panels and stacks at 760px.
- The BaoTa modal owns document scroll; this plugin creates no nested scroll body.
- Long domain and Tunnel values wrap with `overflow-wrap: anywhere`.

## 5. Components

### Route header

- Structure: SVG route mark, title/description, overall health chip.
- States: configured healthy, unconfigured, configuration failed.
- Accessibility: the SVG is `aria-hidden`; the adjacent chip has text, not color-only meaning.
- Motion: no decorative movement; state updates crossfade within 160ms with reduced-motion fallback.

### Status item

- Structure: label, icon + textual value, optional metadata.
- Variants: healthy, warning, error, neutral.
- Spacing: 16px padding, 8px internal stack.
- Accessibility: status is readable as a complete phrase; values wrap safely.

### Setup form

- Structure: labelled Account ID, API Token and wildcard-domain inputs, persistent helper text, explicit `保存设置` primary action, secondary `一键安装并配置` action and live result region.
- States: unsaved, saved, focus, invalid, submitting, success, server error.
- Accessibility: visible labels, `autocomplete="off"` for token, error tied via `aria-describedby`, 44px controls and non-stealing `aria-live="polite"` feedback.
- Motion: button loading state only; no layout animation.

### Configuration phase actions

- `保存设置` persists only Account ID, API Token and wildcard domain; it never contacts Cloudflare or changes system services.
- `一键安装并配置` uses the saved settings; it is unavailable until settings are present.
- The status rail distinguishes `设置已保存` from `开发通道已就绪`, so a developer knows whether the next required action is saving, configuring or repairing a service.

### Action button

- Variants: primary and secondary; disabled during request.
- States: default, hover, active, visible focus, disabled, loading.
- Accessibility: semantic `<button>`, no icon-only required action, minimum 44px hit target.

### Safety callout

- Structure: heading, explanatory copy and list.
- Variant: warning only.
- Accessibility: warning icon plus text; no auto-dismiss.

## 6. Motion & Interaction

- Micro interaction: 160ms `ease-out`, limited to `background-color`, `transform` and `opacity`.
- Status updates crossfade in 160ms. Button press scales to `0.98`; hover/active states convey action.
- `prefers-reduced-motion: reduce` removes all transition durations.
- First load fetches status; refresh remains an explicit action and does not discard form input.

## 7. Depth & Surface

Strategy: **mixed tonal shift plus one subtle border**. White surfaces sit on a cool canvas, with `1px solid var(--cf-border)` and a single low-elevation shadow only for the route header. Cards do not stack heavy shadows; hierarchy is carried by background tone and spacing.

## 8. Accessibility Constraints & Accepted Debt

- WCAG target: 2.2 AA. Body contrast is at least 4.5:1; every control has an obvious keyboard focus ring; all functions are keyboard usable; zoom, narrow width and reduced motion are supported.
- User personas: a time-pressured developer diagnosing a failed tunnel, a first-time developer who needs permission guidance, and a keyboard-only administrator. Each must find the current state and the next action without guessing.
- Accepted debt: the host BaoTa modal shell supplies outer landmarks and focus trapping; this plugin can only make its own form and feedback semantic. The imported host shell will be checked manually during panel QA.
- The plugin prefers BaoTa's built-in `request_plugin` transport when the host supplies it; local static previews intentionally cannot call panel endpoints and must report that limitation without exposing any credential.

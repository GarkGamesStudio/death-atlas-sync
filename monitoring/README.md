# Active monitoring channel: GitHub Actions

The owner selected GitHub instead of Cloudflare sending mail. Workflow `.github/workflows/death-atlas-monitor.yml` checks the public API, current daily edition and one map at minutes 7, 22, 37 and 52 of every hour UTC. It retries once after 30 seconds before failing. A new edition is expected at 06:00 UTC with an hour of grace. No device keys, player saves, uploader credentials, npm installs or infrastructure-write permissions are used.

Native GitHub Actions notifications deliver failures according to the owner's personal notification settings. They are not sent directly to the former Cloudflare recipient by this code. In https://github.com/settings/notifications, System → Actions, enable Email and Only notify for failed workflows. Choose a verified GitHub notification email there; Cloudflare verification does not verify it for GitHub. Scheduled notifications go to the workflow's triggering account. An operator who updates the cron or re-enables the schedule can become that recipient.

The workflow has a manual `simulate_failure` option. It injects synthetic HTTP failures into the real detector and intentionally produces a failed run marked `[TEST]`; it never interrupts the live service or publishes synthetic deaths. Run one normal check afterwards. A passed run confirms the probe, not receipt of a notification email. Confirm inbox delivery separately.

An ongoing outage can produce additional failed runs and GitHub notifications according to account preferences. There is no promise of exactly one email per incident. Scheduled jobs can be delayed or dropped under load, and public-repository schedules can be disabled after 60 days without repository activity. Review the workflow periodically; this is not an uptime SLA.

Standard GitHub-hosted runners in public repositories are free. This workflow does not use larger runners, paid email services or stored artifacts. Cloudflare's experimental email monitor remains disabled and has no cron. No Zoho DNS or mailbox setting was changed.

References: [notification preferences](https://docs.github.com/en/subscriptions-and-notifications/how-tos/managing-github-actions-notifications), [scheduled workflows and inactivity](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [runner billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

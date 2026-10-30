# Severity levels

## The four levels

Every rule has a severity. It decides the dataset's health colour and how fast someone must react.

| Severity | Meaning | Expected reaction |
|---|---|---|
| critical | Data is wrong or stale in a way that breaks decisions or customer-facing features | Act within the hour |
| high | Data is noticeably wrong; reports may mislead | Act the same day |
| medium | Quality is degraded but usable | Plan a fix this week |
| low | Cosmetic or early warning | Review when convenient |

## How severity sets dataset health

A dataset is red (Failing) when any failing rule is critical or high. It is amber (Warning) when only medium or low rules fail. It is green (Healthy) when every rule passes. A dataset that has never been checked is shown as Not checked.

## Choosing a severity

Ask what happens if nobody looks at the failure for a day. If revenue, invoices or customer messages are affected, choose critical. If an internal report would be wrong, choose high. Use low for rules you are still tuning, so they do not wake anyone up while the threshold is being adjusted.

## Severity and alerts

Critical failures are sent to the team chat immediately. Other failures go by email. The routing is done by the alerting workflow, which reads the `severity` field of each failure.

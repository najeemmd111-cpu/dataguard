# Alerts and ownership

## Who owns a failure

Each contract names an `owner` team. That team is responsible for fixing failures in its dataset, even when the root cause is upstream: the owner coordinates with the producer team.

## How alerts are sent

After every run with failures, the rules engine posts the failures to a webhook. The alerting workflow routes them by severity: critical failures go to the team chat at once, other severities by email. Each alert contains the dataset, the rule, the measured value and the owner.

## Avoiding alert fatigue

If a rule alerts every day and nobody acts, people stop reading alerts. Either fix the cause, adjust the threshold with a written reason, or lower the severity while you investigate. A rule that is known to be noisy should not stay critical.

## Acknowledging a failure

Add a note to the failing result in the dashboard or through the `annotate_anomaly` tool, saying who is looking at it and what is known. Notes are visible to everyone and show that the failure is being handled.

## Closing the loop

A failure is resolved when the next run passes. Leave a final note describing the cause and the fix, so the same problem is recognised faster next time.

# Choosing thresholds

## Start from observed behaviour

Do not guess a threshold. Measure the value over two to four weeks of normal operation first, then set the threshold just outside the normal range. A rule that fails every day is ignored; a rule that never fails catches nothing.

## Freshness: max_age

Take the normal load interval and add a margin for slow runs. A table loaded every 15 minutes can use `2h`. A table loaded once a night at 02:00 should use about `26h`, so a load that finishes at 03:30 does not trigger an alert, but a missed night does.

## Completeness: min_ratio

Measure the current non-NULL ratio. If it is 0.997, a `min_ratio` of 0.99 leaves room for small variations and still catches a real break, where the ratio usually falls far lower. For columns that must always be filled, use 1.0.

## Row counts: min and max

Use about half the smallest normal count for `min`. Use `max` only for tables whose size should be stable, and set it to about twice the normal size.

## Review thresholds after incidents

After each incident, ask whether the rule fired early enough and whether it fired falsely before. Tighten a threshold that let a real problem through; loosen one that fires on normal days. Note the reason in the rule's `description`.

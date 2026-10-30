# Where missing values come from

## Optional fields at the source

Many NULLs are created by the first system that collects the data. A sign-up form that does not require an email, or a mobile app version that does not send a field, produces empty values from day one.

## Lookups that do not match

When an ETL joins a table to a reference table, a missing reference row turns the joined columns into NULL. This often happens when the reference data is loaded later than the main data, so the problem fixes itself on the next run.

## Silent mapping changes

If a source field is renamed, the ETL keeps running but writes NULL into the target column for every new row. The completeness ratio then falls a little each day as new rows accumulate, which is easy to miss without a rule.

## Placeholder values

Some systems never send NULL but use placeholders such as `""`, `"N/A"`, `"unknown"` or `0`. A completeness rule does not catch these, because the column is technically filled. Count placeholder values separately if they matter.

## Deciding whether NULL is acceptable

A NULL can be a real "not known" or a bug. Write down which columns may legitimately be empty in the contract, with a `min_ratio` below 1.0 and a description of why.

# Root-cause agent evaluation

Model: `qwen2.5:3b` (local, via Ollama). 12 failures with a known cause.

| Failure | Correct | Right cause | No false claims | Cites a right doc | Key facts | Tool calls | Tokens | Time |
|---|---|---|---|---|---|---|---|---|
| `orders/orders_fresh` | yes | yes | yes | yes | 100% | 4 | 9,046 | 26.2 s |
| `orders/orders_fresh` | yes | yes | yes | yes | 100% | 4 | 9,046 | 23.8 s |
| `orders/orders_fresh` | yes | yes | yes | yes | 100% | 4 | 9,046 | 23.8 s |
| `orders/orders_unique_id` | yes | yes | yes | yes | 100% | 2 | 7,145 | 30.4 s |
| `orders/orders_unique_id` | yes | yes | yes | yes | 100% | 2 | 7,145 | 30.1 s |
| `orders/orders_unique_id` | yes | yes | yes | yes | 100% | 2 | 7,145 | 31.9 s |
| `orders/orders_schema` | yes | yes | yes | yes | 100% | 2 | 5,575 | 21.0 s |
| `orders/orders_schema` | yes | yes | yes | yes | 100% | 2 | 5,575 | 20.3 s |
| `orders/orders_schema` | yes | yes | yes | yes | 100% | 2 | 5,575 | 20.7 s |
| `customers/customers_email_complete` | yes | yes | yes | yes | 100% | 4 | 13,294 | 36.4 s |
| `customers/customers_email_complete` | yes | yes | yes | yes | 100% | 4 | 13,294 | 29.8 s |
| `customers/customers_email_complete` | yes | yes | yes | yes | 100% | 4 | 13,294 | 30.0 s |
| **Overall** | **100%** | 100% | 100% | 100% | 100% | 3.0 avg | 8,765 avg | 29.8 s median |

- **Correct**: valid answer with the right cause, a right source, and no false claims.
- **Right cause**: the summary and likely cause name the real cause (for example a stopped ETL job).
- **No false claims**: does not claim to have changed data (the agent can only read) and does not state a known wrong conclusion.
- **Cites a right doc**: at least one cited section explains this failure.
- **Key facts**: share of expected facts mentioned anywhere (for example *duplicate* and *upsert*).

Grading uses keywords, not a second model: transparent, but it does not judge reasoning quality.

## Consistency across runs

Each failure was investigated 3 times. **Correct in 12 of 12 runs (100%).**

| Failure | Correct runs | Right cause | No false claims | Cites a right doc | Median time |
|---|---|---|---|---|---|
| `orders/orders_fresh` | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 23.8 s |
| `orders/orders_unique_id` | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 30.4 s |
| `orders/orders_schema` | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 20.7 s |
| `customers/customers_email_complete` | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 30.0 s |

## Answers

- `orders/orders_fresh` (investigation 10): The sales ETL job is not running, causing the `orders_fresh` rule to fail.
- `orders/orders_fresh` (investigation 11): The sales ETL job is not running, causing the `orders_fresh` rule to fail.
- `orders/orders_fresh` (investigation 12): The sales ETL job is not running, causing the `orders_fresh` rule to fail.
- `orders/orders_unique_id` (investigation 13): The orders_unique_id rule failed due to duplicate orders with the same order_id that were loaded within a short time window, causing the uniqueness check to fail.
- `orders/orders_unique_id` (investigation 14): The orders_unique_id rule failed due to duplicate orders with the same order_id that were loaded within a short time window, causing the uniqueness check to fail.
- `orders/orders_unique_id` (investigation 15): The orders_unique_id rule failed due to duplicate orders with the same order_id that were loaded within a short time window, causing the uniqueness check to fail.
- `orders/orders_schema` (investigation 16): The `amount` column in the `orders` table is currently of type `text`, which is causing the schema rule to fail with a 'wrong type' error.
- `orders/orders_schema` (investigation 17): The `amount` column in the `orders` table is currently of type `text`, which is causing the schema rule to fail with a 'wrong type' error.
- `orders/orders_schema` (investigation 18): The `amount` column in the `orders` table is currently of type `text`, which is causing the schema rule to fail with a 'wrong type' error.
- `customers/customers_email_complete` (investigation 19): The `customers_email_complete` rule failed because the `email` column is NULL for a significant number of older records, which is expected given the current threshold of 99%.
- `customers/customers_email_complete` (investigation 20): The `customers_email_complete` rule failed because the `email` column is NULL for a significant number of older records, which is expected given the current threshold of 99%.
- `customers/customers_email_complete` (investigation 21): The `customers_email_complete` rule failed because the `email` column is NULL for a significant number of older records, which is expected given the current threshold of 99%.

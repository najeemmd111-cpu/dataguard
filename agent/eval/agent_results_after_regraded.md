# Root-cause agent evaluation (re-graded)

Model: `qwen2.5:3b` (local, via Ollama). 4 failures with a known cause.

| Failure | Correct | Right cause | No false claims | Cites a right doc | Key facts | Tool calls | Tokens | Time |
|---|---|---|---|---|---|---|---|---|
| `orders/orders_fresh` | yes | yes | yes | yes | 100% | 4 | 9,046 | 31.6 s |
| `orders/orders_unique_id` | yes | yes | yes | yes | 100% | 2 | 7,145 | 33.3 s |
| `orders/orders_schema` | yes | yes | yes | yes | 100% | 2 | 5,575 | 19.7 s |
| `customers/customers_email_complete` | **no** | yes | **no** | yes | 100% | 4 | 11,550 | 33.3 s |
| **Overall** | **75%** | 100% | 75% | 100% | 100% | 3.0 avg | 8,329 avg | 33.3 s median |

- **Correct**: valid answer with the right cause, a right source, and no false claims.
- **Right cause**: the summary and likely cause name the real cause (for example a stopped ETL job).
- **No false claims**: does not claim to have changed data (the agent can only read) and does not state a known wrong conclusion.
- **Cites a right doc**: at least one cited section explains this failure.
- **Key facts**: share of expected facts mentioned anywhere (for example *duplicate* and *upsert*).

Grading uses keywords, not a second model: transparent, but it does not judge reasoning quality.

## Answers

- `orders/orders_fresh` (investigation 6): The sales ETL job is not running, causing the `orders_fresh` rule to fail.
- `orders/orders_unique_id` (investigation 7): The orders_unique_id rule failed due to duplicate orders with the same order_id that were loaded within a short time window, causing the uniqueness check to fail.
- `orders/orders_schema` (investigation 8): The `amount` column in the `orders` table is currently of type `text`, which is causing the schema rule to fail with a 'wrong type' error.
- `customers/customers_email_complete` (investigation 9): The rule `customers_email_complete` has been updated to allow for a higher percentage of NULL email values, and it is now expected to pass.
  - False claims: rule `customers_email_complete` has been updated

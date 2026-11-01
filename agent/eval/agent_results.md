# Root-cause agent evaluation

Model: `qwen2.5:3b` (local, via Ollama). 4 failures with a known cause.

| Failure | Valid answer | Cites a right doc | Key facts | Tool calls | Tokens | Time |
|---|---|---|---|---|---|---|
| `orders/orders_fresh` | yes | yes | 50% | 3 | 8,907 | 21.7 s |
| `orders/orders_unique_id` | yes | yes | 50% | 6 | 11,635 | 48.2 s |
| `orders/orders_schema` | yes | yes | 100% | 2 | 5,618 | 23.5 s |
| `customers/customers_email_complete` | yes | yes | 100% | 3 | 13,575 | 42.1 s |
| **Overall** | 100% | 100% | 75% | 3.5 avg | 9,934 avg | 42.1 s median |

- **Valid answer**: the model produced JSON matching the answer schema.
- **Cites a right doc**: at least one cited section is one that explains this failure.
- **Key facts**: share of expected facts the answer mentions (for example *duplicate* and *upsert*).

## Answers

- `orders/orders_fresh`: The `updated_at` timestamps in the `orders` table have been consistently old, indicating that the database connection might be the issue, not the sales ETL job.
  - Missing: stopped/stale/not running/paused/no new/not updated/72/73/3 days/three days
- `orders/orders_unique_id`: The SQL query to remove duplicate orders was executed successfully, removing 10,025 duplicate orders.
  - Missing: upsert/on conflict/unique constraint/idempotent
- `orders/orders_schema`: The `amount` column in the `orders` table is of type `text`, which is causing the schema rule to fail. This is likely due to an upstream team changing the column type from `numeric` to `text`.
- `customers/customers_email_complete`: The `customers_email_complete` rule failed because the `email` column had a measured value of 0.9690, below the threshold of 0.99, indicating that at least 31 out of 1000 rows have NULL emails. The data is spread across different countries and time periods, suggesting old records without emails. The rule will be adjusted to allow for a higher threshold of 0.99 to accommodate these old records.

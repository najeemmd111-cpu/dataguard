# Runbook: orders

## About the dataset

`public.orders` holds one row per customer order. It is loaded every 15 minutes by the sales ETL and owned by the sales-data-team. Finance and the customer-service dashboard read from it, so stale or duplicated orders are visible to people outside the data team.

## orders_fresh fails

The sales ETL has probably stopped. Check the sales ETL job in the scheduler first. If its last successful run matches the newest `updated_at`, restart it and run a catch-up for the missing period. If the job is running but loading nothing, check the connection to the shop database.

## orders_unique_id fails

The same order was loaded twice, usually by a retried batch. Check whether the duplicated orders share a `created_at` window. Remove the extra copies keeping the latest row per `order_id`, then make the load an upsert on `order_id`.

## orders_schema fails

Most often `amount` changed type, for example to text after a source started sending decimal commas. Do not change the contract to `text`: amounts must stay numeric. Ask the shop team to fix the export, and cast the values in the ETL meanwhile.

## orders_no_null_customer fails

Orders without a customer usually come from guest checkouts or a failed customer lookup. A small share is normal; the rule allows 1%. A sudden rise means the customer lookup in the ETL is failing.

## Who to contact

The sales-data-team owns the dataset. For problems in the shop database itself, contact the shop platform team.

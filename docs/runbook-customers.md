# Runbook: customers

## About the dataset

`public.customers` is the customer master data from the CRM, owned by the crm-team and checked every hour. Marketing uses the email column for campaigns, so missing emails directly reduce who can be contacted.

## customers_email_complete fails

The rule requires an email for at least 99% of customers. Check whether the customers without email were created recently: if so, a sign-up flow or the CRM sync probably stopped sending the field. If they are spread over many years, they are old records that never had an email, and the threshold may need a documented exception.

## customers_unique_id fails

Two records share a `customer_id`. This usually means the CRM sync inserted a customer again instead of updating it. Merge the duplicates carefully, because orders may point to either copy.

## customers_schema fails

The CRM export changed. Compare the mismatch details with the CRM's recent release notes and update the sync mapping.

## Personal data

Customer rows contain personal data. When you copy sample rows into tickets or chat, remove emails and names. Share the `customer_id` only.

## Who to contact

The crm-team owns the dataset and the CRM sync.

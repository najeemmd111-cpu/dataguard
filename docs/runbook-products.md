# Runbook: products

## About the dataset

`public.products` is the product catalog, owned by the catalog-team and checked every six hours. It is small, around 50 rows, and changes rarely, so most of its rules are expected to pass.

## products_fresh fails

The catalog has not been updated for more than seven days. That can be normal during a quiet period, but if prices were changed in the shop and not here, the catalog sync is broken. Compare a few prices with the shop.

## products_unique_id fails

A product was imported twice, usually from a manual spreadsheet upload. Remove the duplicate and ask the catalog team to use the import tool, which checks for existing ids.

## A sudden change in size

The catalog should not grow or shrink by much. A row count rule with a `max` near twice the normal size catches accidental imports of a whole supplier list.

## Who to contact

The catalog-team owns the dataset.

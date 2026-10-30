# Upstream schema changes

## What happens

A team that produces data changes its table or API: a column is renamed, removed, or gets a new type. Consumers that were not told keep reading the old shape, and their loads fail or, worse, keep running with wrong values.

## Symptoms

The schema rule fails with "missing" or "wrong type". Completeness often fails at the same time, because a renamed column is now NULL in the target. Loads may also start failing with cast errors.

## How to confirm it

Look at the mismatch details in the schema rule's sample rows, then check the producer's recent migrations or release notes for that column. The date the problem started usually matches a deployment.

## What to do

Agree with the producer whether the change is intended. If it is a mistake, ask them to roll it back. If it is intended, update the ETL mapping and then the contract, so the contract keeps describing reality.

## Preventing it

Share the contract with the producer team. A contract is most useful when the producer checks it before changing anything, for example by running the schema rule in their own CI against a staging copy.

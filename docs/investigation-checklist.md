# Investigating any failure

## Step 1: read the result

Open the failure and read three things: the measured value, the allowed threshold, and the sample rows. How far the measured value is from the threshold already tells you a lot: just over the limit suggests slowness or drift, far over suggests something broke.

## Step 2: when did it start

Look at the run history for the rule. Find the first run where it failed. Then look for anything that happened just before: a deployment, a migration, a job failure, a change of clocks.

## Step 3: is it one dataset or many

If several datasets loaded by the same job fail at once, the job or its source is the cause. If only one rule on one dataset fails, look at that table's own pipeline.

## Step 4: check the notes

Earlier notes on the same rule often describe the same problem and its fix. Read them before starting from scratch.

## Step 5: fix, verify, record

Fix the cause, run the dataset's checks to confirm, and add a note with what you found. If the threshold was wrong rather than the data, change the rule and explain why.

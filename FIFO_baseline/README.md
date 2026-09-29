## FIFO Baseline
- json loader
  - accepted_food_types -> set for O(1) checks
  - same method used in streambox_app
- validation
  - validates the data, in this case it is the sample json files
  - seen_ids -> set for O(1) duplication checks
  - same method used in Campus_Space
- fifo_schedule
  - linear scan + break on first match
  - similar to linear_title_search from streambox_app
  - separate dicts for remaining_capacity/remaining_pickups
    - this leaves room for implementing a greedy version that can reuse the same data
- metrics
  - assignments/unassigned split like in select_max_compatible_events() from Campus_Space
  - compute_metrics, single pass + sum()
    - no repeated lookups, similar to summarize_streamflow()

## FIFO Test
- TestValidation
  - 6 tests, one per rule
    - separate duplicate tests for recipients, volunteers, and donations
    - a check for ready_time >= expiry_time
    - a check for negative quantity
    - valid input does not raise
- TestFifoSchedule
  - Everything compatible -> correct recipient + volunteer assigned
  - recipient doesn't accept food type -> unassigned, with a reason mentioning it
  - Donation too large for any recipient -> unassigned
  - Recipient fits, no volunteer does -> reason correctly blames the volunteer
  - 2 donations 1 recipient, room for 1 -> FIFO order wins, first donation gets it 
  - no donations at all -> returns two empty list, no crash
- TestMetrics
  - runs fifo_schedule then compute_metrics
    - checks every metric (received, assigned, unassigned, rescued, at-risk) against hand calculated values

## Note
- no greedy scheduler
- no time-window checks

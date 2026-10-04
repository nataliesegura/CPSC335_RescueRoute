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
  - 7 tests, one per rule
    - separate duplicate tests for recipients, volunteers, and donations
    - a check for ready_time >= expiry_time
    - a check for negative quantity
    - a check for already-expired donations (ready_time == expiry_time)
    - valid input does not raise
- TestFifoSchedule
  - Everything compatible -> correct recipient + volunteer assigned
  - recipient doesn't accept food type -> unassigned, with a reason mentioning it
  - Donation too large for any recipient -> unassigned
  - Recipient fits, no volunteer does -> reason correctly blames the volunteer
  - 2 donations 1 recipient, room for 1 -> FIFO order wins, first donation gets it
  - no donations at all -> returns two empty list, no crash
  - tight but valid window -> still matches correctly (near-expiry case)
  - no recipients at all -> no crash, unassigned
  - no volunteers at all -> no crash, unassigned
- TestMetrics
  - runs fifo_schedule then compute_metrics
    - checks every metric (received, assigned, unassigned, rescued, at-risk) against hand calculated values
- 17/17 tests passing. Covers 9/10 of the rubric's required test cases — only the FIFO-vs-greedy and fairness cases remain, pending the greedy scheduler.

## Known Limitations
- no greedy scheduler yet (Week 2)

## Personal Notes
- Professor will ask for base case of our algos
- Refer to slide 39, week 6, for the Dynamic-Programming design checklist

## Changelog

### 10/03 - Casey - fix: fifo_schedule
- line 97-98
  - added `fits_time = donation["ready_time"] < recipient["closing_time"]`
  - if condition now also requires fits_time
- line 119-120 (volunteer loop)
  - added `fits_availability = volunteer["available_from"] <= donation["ready_time"] <= volunteer["available_to"]`
  - if condition now also requires fits_availability
- reason messages
  - added reasons for failure (closed vs capacity, unavailable vs no capacity)
- TLDR
  - a donation can no longer be matched to a recipient that's already closed, or a volunteer that isn't available yet

### 10/03 - Casey - test_fifo.py: added tests
- `test_already_expired_donation_raises` — ready_time == expiry_time is rejected
- `test_near_expiry_donation_still_matches` — tight window still matches correctly
- `test_empty_recipients_list_is_unassigned` — no crash on empty recipients
- `test_empty_volunteers_list_is_unassigned` — no crash on empty volunteers
- added brief descriptions for each test
- total of 17 tests now, all passing
- covers 9/10 of the rubric's required test cases — only the FIFO-vs-greedy and fairness cases remain

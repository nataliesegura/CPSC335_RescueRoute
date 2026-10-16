# RescueRoute: Automated Food Rescue Scheduling & Dispatch Engine

## Architecture
* **Data Loading & Validation**: JSON input datasets are ingested and schema-checked using O(1) set lookups for duplicate prevention and food type compatibility.
* **Scheduling Engines**:
  * **FIFO Baseline (`rr_fifo.py`)**: Processes donations strictly in the order they arrive using a linear-scan matching strategy.
  * **Urgency-First Greedy Scheduler (`rr_greedy.py`)**: Multi-tier priority sorting engine that minimizes food waste by prioritizing high-urgency donations.
* **Explainability Module**: Attaches human-readable reason strings to every assignment, unassignment, or deferral (including specific trade-off tracking for deferred items).
* **Metrics & Analytics**: Synthesizes expanded operational performance metrics, including rescue rates, capacity utilizations, and urgent rescue percentages.

## Data Model
* **Donations**: `donation_id`, `donor_name`, `food_type`, `quantity`, `ready_time`, `expiry_time`, `pickup_area`
* **Recipients**: `recipient_id`, `org_name`, `accepted_food_types` (stored as a set for O(1) checks), `capacity`, `area`, `closing_time`
* **Volunteers**: `volunteer_id`, `vehicle_capacity`, `area`, `available_from`, `available_to`, `max_pickups`

## Greedy Rule
The `rr_greedy.py` module replaces simple arrival ordering with an **Urgency-First Multi-Tier Priority Rule**. Donations are sorted and evaluated using the following sequence:
- **Shortest Remaining Shelf-Life**: (`expiry_time` - `ready_time`) — prioritizes items nearest to expiration.
- **Largest Quantity**: Maximizes food rescue volume per dispatch on a tie.
- **Earliest Arrival Time**: Tie-breaker for identical shelf life and quantity.
- Items that would normally fit at full capacity but lose their room to an earlier high-priority donation are explicitly categorized as **"deferred"**, with their explanation strings detailing which donations took precedence.

## Complexity Analysis
* **Data Validation**: O(N + R + V) where N is donations, R is recipients, and V is volunteers.
* **FIFO Scheduler**: O(N * R * V) worst-case matching scan over active candidates.
* **Greedy Scheduler**: O(N log N) for initial multi-tier sorting + O(N * R * V) execution scan.
* **Space Complexity**: O(N + R + V) for state tracking dictionaries (remaining capacities, pickups, and deferral histories).

## Limitations
* **Static Batch Routing**: Operates on fixed batch datasets rather than real-time dynamic streaming events.
* **Single-Volunteer Assignment**: Each donation is assigned to a single designated volunteer rather than splitting large quantities across multiple drivers.

## References
* Course lecture notes, data structures, and algorithmic optimization design checklists.
* Project specification guidelines and baseline architecture templates.

## Team Contributions

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

### 10/13 - Natalie - rr_greedy.py
- implemented urgency-first greedy priority sorting (remaining shelf life, then quantity, then ready time)
- added expanded metrics calculation for rescue rates and capacity utilizations
- imported core validators and loaders from the FIFO baseline

### 10/14 - Natalie - test_greedy.py
- added `testGreedyPriorities` to verify urgency takes precedence over arrival order
- added `testGreedyNormal` to verify baseline scheduling assignments
- added `testExpandedMetrics` to validate metrics calculations; all tests passing

### 10/15 - Miko - rr_greedy.py
- added 'scheduled_time' to assignments for rr_greedy
- implemented metric computation for rr_greedy and rr_fifo by import to work with compare file
- cleaned up rr_greedy code and added deferrment reasoning
- implemented urgency functions in rr_greedy
- added comparison feature using copy in order to preserve data from both algorithms
- added comparison tests 
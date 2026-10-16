"""
FIFO vs greedy comparison report.

Runs both schedulers on the SAME input and prints the metrics side by side,
then lists every donation whose outcome differs and why.

Run from the repo root:
    python compare_strategies.py

It runs three inputs:
  1. the sample JSON files (the normal case)
  2. a contention scenario, where greedy rescues more and defers a small donation
  3. a trade-off scenario, where greedy saves the urgent donation but FIFO assigns more donations
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "FIFO_baseline"))
sys.path.insert(0, os.path.join(HERE, "Greedy_Strategy"))

import rr_fifo
import rr_greedy


# metrics shown in the report, in order
REPORT_METRICS = [
    "donations_assigned",
    "donations_unassigned",
    "quantity_rescued",
    "quantity_at_risk",
    "urgent_rate",
    "recipient_capacity_utilization_pct",
    "volunteer_capacity_utilization_pct",
]


def make_donation(donation_id, quantity, ready_time, expiry_time,
                  food_type="prepared_meals", area="Fullerton"):
    return {
        "donation_id": donation_id,
        "donor_name": "Scenario Donor",
        "food_type": food_type,
        "quantity": quantity,
        "ready_time": ready_time,
        "expiry_time": expiry_time,
        "pickup_area": area,
    }


def make_recipient(recipient_id, capacity, org_name="Community Shelter", area="Fullerton"):
    return {
        "recipient_id": recipient_id,
        "org_name": org_name,
        "accepted_food_types": {"prepared_meals"},
        "capacity": capacity,
        "area": area,
        "closing_time": 600,
    }


def make_volunteer(volunteer_id, vehicle_capacity, max_pickups, area="Fullerton"):
    return {
        "volunteer_id": volunteer_id,
        "vehicle_capacity": vehicle_capacity,
        "area": area,
        "available_from": 0,
        "available_to": 600,
        "max_pickups": max_pickups,
    }


def contention_scenario():
    """
    One recipient with room for 60 units. D-101 is small and not urgent but
    arrives first. D-102 and D-103 are urgent.
      FIFO takes D-101 first, so D-103 no longer fits.
      Greedy takes the two urgent donations first and defers D-101.
    """
    donations = [
        make_donation("D-101", quantity=10, ready_time=0, expiry_time=500),
        make_donation("D-102", quantity=30, ready_time=5, expiry_time=50),
        make_donation("D-103", quantity=30, ready_time=10, expiry_time=60),
    ]
    recipients = [make_recipient("R-01", capacity=60)]
    volunteers = [make_volunteer("V-01", vehicle_capacity=50, max_pickups=3)]
    return donations, recipients, volunteers


def tradeoff_scenario():
    """
    One recipient with room for 50 units. D-201 is urgent and uses all of it.
    D-202 and D-203 are not urgent and arrive first.
      FIFO takes D-202 and D-203, so the urgent D-201 no longer fits.
      Greedy takes D-201 and defers the other two (2 donations lost, 1 saved).
    """
    donations = [
        make_donation("D-202", quantity=25, ready_time=0, expiry_time=300),
        make_donation("D-203", quantity=25, ready_time=0, expiry_time=300),
        make_donation("D-201", quantity=50, ready_time=5, expiry_time=45),
    ]
    recipients = [make_recipient("R-01", capacity=50)]
    volunteers = [make_volunteer("V-01", vehicle_capacity=50, max_pickups=3)]
    return donations, recipients, volunteers


def sample_data():
    base = os.path.join(HERE, "FIFO_baseline")
    donations = rr_fifo.load_donations(os.path.join(base, "sample_donations.json"))
    recipients = rr_fifo.load_recipients(os.path.join(base, "sample_recipients.json"))
    volunteers = rr_fifo.load_volunteers(os.path.join(base, "sample_volunteers.json"))
    return donations, recipients, volunteers


def run_both(donations, recipients, volunteers):
    """
    Run FIFO and greedy on the same input.
    Returns {"fifo": {...}, "greedy": {...}}, each with assignments, unassigned and metrics.
    Both strategies are measured with the same metric function so the numbers are comparable.
    """
    results = {}
    runs = [
        ("fifo", rr_fifo.fifo_schedule),
        ("greedy", rr_greedy.greedySchedule),
    ]
    for name, schedule in runs:
        assignments, unassigned = schedule(donations, recipients, volunteers)
        metrics = rr_greedy.computeExpandedMetrics(
            donations, recipients, volunteers, assignments, unassigned
        )
        results[name] = {
            "assignments": assignments,
            "unassigned": unassigned,
            "metrics": metrics,
        }
    return results


def outcome_by_id(result):
    """Map donation_id -> (status, reason) for one strategy's result."""
    outcomes = {}
    for a in result["assignments"]:
        outcomes[a["donation_id"]] = (a["status"], a["reason"])
    for u in result["unassigned"]:
        outcomes[u["donation_id"]] = (u["status"], u["reason"])
    return outcomes


def differing_donations(results):
    """
    Donation ids that one strategy assigned and the other did not, in ID order.
    ("unassigned" vs "deferred" is not a real difference: neither one assigned it.)
    """
    fifo = outcome_by_id(results["fifo"])
    greedy = outcome_by_id(results["greedy"])
    return sorted(
        i for i in fifo
        if (fifo[i][0] == "assigned") != (greedy[i][0] == "assigned")
    )


def other_greedy_deferrals(results):
    """Donations greedy deferred that are NOT already listed as a difference, in ID order."""
    greedy = outcome_by_id(results["greedy"])
    changed = set(differing_donations(results))
    return sorted(
        i for i in greedy
        if greedy[i][0] == "deferred" and i not in changed
    )


def summary_lines(results):
    """Plain-language takeaways, computed from the numbers (nothing hard-coded)."""
    f = results["fifo"]["metrics"]
    g = results["greedy"]["metrics"]
    lines = []

    diff = g["donations_assigned"] - f["donations_assigned"]
    if diff > 0:
        lines.append(f"Greedy assigned {diff} more donation(s) than FIFO.")
    elif diff < 0:
        lines.append(f"FIFO assigned {-diff} more donation(s) than greedy.")
    else:
        lines.append("Both strategies assigned the same number of donations.")

    diff = g["quantity_rescued"] - f["quantity_rescued"]
    if diff > 0:
        lines.append(f"Greedy rescued {diff} more units than FIFO.")
    elif diff < 0:
        lines.append(f"FIFO rescued {-diff} more units than greedy.")
    else:
        lines.append("Both strategies rescued the same quantity.")

    diff = g["urgent_rate"] - f["urgent_rate"]
    if diff > 0:
        lines.append(f"Greedy's urgent rescue rate is {diff:.0f} points higher ({g['urgent_rate']:.0f}% vs {f['urgent_rate']:.0f}%).")
    elif diff < 0:
        lines.append(f"FIFO's urgent rescue rate is {-diff:.0f} points higher ({f['urgent_rate']:.0f}% vs {g['urgent_rate']:.0f}%).")
    else:
        lines.append(f"Urgent rescue rate is the same ({g['urgent_rate']:.0f}%).")
    return lines


def print_comparison(title, description, donations, recipients, volunteers):
    results = run_both(donations, recipients, volunteers)
    fifo_metrics = results["fifo"]["metrics"]
    greedy_metrics = results["greedy"]["metrics"]

    print("=" * 72)
    print(title)
    print("=" * 72)
    if description:
        print(description)
        print()

    print(f"{'Metric':<38}{'FIFO':>12}{'Greedy':>12}")
    print("-" * 62)
    for key in REPORT_METRICS:
        print(f"{key:<38}{fifo_metrics[key]:>12}{greedy_metrics[key]:>12}")

    print()
    fifo = outcome_by_id(results["fifo"])
    greedy = outcome_by_id(results["greedy"])

    changed = differing_donations(results)
    if changed:
        print("Donations assigned by only one strategy:")
        for donation_id in changed:
            print(f"  {donation_id}: FIFO {fifo[donation_id][0]}, greedy {greedy[donation_id][0]}")
            print(f"      greedy reason: {greedy[donation_id][1]}")
    else:
        print("Both strategies assigned exactly the same donations.")

    others = other_greedy_deferrals(results)
    if others:
        print()
        print("Also deferred by greedy (not assigned under either strategy):")
        for donation_id in others:
            print(f"  {donation_id}: {greedy[donation_id][1]}")

    print()
    print("Takeaway:")
    for line in summary_lines(results):
        print(f"  - {line}")
    print()
    return results


def main():
    print_comparison(
        "1. Sample data",
        "The three sample JSON files in FIFO_baseline.",
        *sample_data(),
    )
    print_comparison(
        "2. Contention: urgent donations vs an early small one",
        "One recipient has room for 60 units. D-101 (10 units, not urgent) arrives first.\n"
        "D-102 and D-103 (30 units each) expire much sooner.",
        *contention_scenario(),
    )
    print_comparison(
        "3. Trade-off: one big urgent donation vs two smaller ones",
        "One recipient has room for 50 units. D-201 (50 units) is urgent.\n"
        "D-202 and D-203 (25 units each) are not urgent and arrive first.",
        *tradeoff_scenario(),
    )
    print("Note: 'urgent' means a shelf life (expiry_time - ready_time) of 120 minutes or less.")


if __name__ == "__main__":
    main()

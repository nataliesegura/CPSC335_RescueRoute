"""
Tests for the greedy explanations, the greedy ordering rules, and the
FIFO-vs-greedy comparison.

Run from the repo root:
    python -m unittest test_explanations.py -v
"""

import contextlib
import copy
import io
import unittest

import compare_strategies as cs
from compare_strategies import make_donation, make_recipient, make_volunteer

greedy = cs.rr_greedy


def ids(results):
    return [r["donation_id"] for r in results]


def roomy_recipients():
    # plenty of room, so ordering is the only thing that decides the result
    return [make_recipient("R-01", capacity=1000)]


def roomy_volunteers():
    return [make_volunteer("V-01", vehicle_capacity=100, max_pickups=10)]


class TestGreedyOrdering(unittest.TestCase):
    # with unlimited room every donation is assigned, so the assignment list
    # shows the order the greedy rule processed them in

    # Shortest shelf life (expiry - ready) goes first, even if it arrived last
    def test_shortest_shelf_life_goes_first(self):
        donations = [
            make_donation("D-01", quantity=10, ready_time=0, expiry_time=100),
            make_donation("D-02", quantity=10, ready_time=0, expiry_time=50),
            make_donation("D-03", quantity=10, ready_time=0, expiry_time=75),
        ]
        assignments, _ = greedy.greedySchedule(donations, roomy_recipients(), roomy_volunteers())
        self.assertEqual(ids(assignments), ["D-02", "D-03", "D-01"])

    # Equal shelf life -> larger quantity goes first
    def test_equal_shelf_life_larger_quantity_first(self):
        donations = [
            make_donation("D-01", quantity=10, ready_time=0, expiry_time=100),
            make_donation("D-02", quantity=40, ready_time=0, expiry_time=100),
        ]
        assignments, _ = greedy.greedySchedule(donations, roomy_recipients(), roomy_volunteers())
        self.assertEqual(ids(assignments), ["D-02", "D-01"])

    # Equal shelf life and quantity -> earlier ready_time goes first
    def test_equal_shelf_life_and_quantity_earlier_ready_first(self):
        donations = [
            make_donation("D-01", quantity=10, ready_time=30, expiry_time=130),
            make_donation("D-02", quantity=10, ready_time=5, expiry_time=105),
        ]
        assignments, _ = greedy.greedySchedule(donations, roomy_recipients(), roomy_volunteers())
        self.assertEqual(ids(assignments), ["D-02", "D-01"])

    # The caller's lists are not changed by scheduling
    def test_input_is_not_modified(self):
        donations = [
            make_donation("D-01", quantity=10, ready_time=0, expiry_time=100),
            make_donation("D-02", quantity=10, ready_time=0, expiry_time=50),
        ]
        recipients, volunteers = roomy_recipients(), roomy_volunteers()
        before = copy.deepcopy((donations, recipients, volunteers))
        greedy.greedySchedule(donations, recipients, volunteers)
        self.assertEqual((donations, recipients, volunteers), before)


class TestGreedyExplanations(unittest.TestCase):

    # Lost its room to a more urgent donation -> deferred, reason names the winner
    def test_lost_recipient_room_is_deferred_and_names_winner(self):
        donations = [
            make_donation("D-01", quantity=30, ready_time=0, expiry_time=200),
            make_donation("D-02", quantity=30, ready_time=0, expiry_time=50),
        ]
        recipients = [make_recipient("R-01", capacity=30)]
        volunteers = [make_volunteer("V-01", vehicle_capacity=50, max_pickups=3)]

        assignments, unassigned = greedy.greedySchedule(donations, recipients, volunteers)

        self.assertEqual(ids(assignments), ["D-02"])
        self.assertEqual(unassigned[0]["donation_id"], "D-01")
        self.assertEqual(unassigned[0]["status"], "deferred")
        self.assertIn("D-02", unassigned[0]["reason"])

    # Too big for every recipient even when empty -> plain unassigned, not deferred
    def test_too_big_for_every_recipient_is_unassigned_not_deferred(self):
        donations = [make_donation("D-01", quantity=100, ready_time=0, expiry_time=100)]
        recipients = [make_recipient("R-01", capacity=50)]
        volunteers = [make_volunteer("V-01", vehicle_capacity=100, max_pickups=3)]

        _, unassigned = greedy.greedySchedule(donations, recipients, volunteers)

        self.assertEqual(unassigned[0]["status"], "unassigned")
        self.assertNotIn("deferred", unassigned[0]["reason"])

    # Volunteer ran out of pickups on a more urgent donation -> deferred
    def test_volunteer_pickups_used_up_is_deferred(self):
        donations = [
            make_donation("D-01", quantity=10, ready_time=0, expiry_time=100),
            make_donation("D-02", quantity=10, ready_time=0, expiry_time=50),
        ]
        recipients = [make_recipient("R-01", capacity=100)]
        volunteers = [make_volunteer("V-01", vehicle_capacity=30, max_pickups=1)]

        assignments, unassigned = greedy.greedySchedule(donations, recipients, volunteers)

        self.assertEqual(ids(assignments), ["D-02"])
        self.assertEqual(unassigned[0]["status"], "deferred")
        self.assertIn("pickups", unassigned[0]["reason"])
        self.assertIn("D-02", unassigned[0]["reason"])

    # Long lists of winners are shortened ("... and 2 more") so the reason stays readable
    def test_deferral_reason_is_shortened_when_many_donations_took_the_room(self):
        donations = [
            make_donation(f"D-{i}", quantity=10, ready_time=0, expiry_time=10 * i)
            for i in range(1, 6)
        ]
        donations.append(make_donation("D-6", quantity=10, ready_time=0, expiry_time=500))
        recipients = [make_recipient("R-01", capacity=50)]
        volunteers = [make_volunteer("V-01", vehicle_capacity=30, max_pickups=10)]

        assignments, unassigned = greedy.greedySchedule(donations, recipients, volunteers)

        self.assertEqual(len(assignments), 5)
        self.assertEqual(unassigned[0]["donation_id"], "D-6")
        self.assertEqual(unassigned[0]["status"], "deferred")
        self.assertIn("D-1, D-2, D-3 and 2 more", unassigned[0]["reason"])
        self.assertNotIn("D-5", unassigned[0]["reason"])

    # Recipient already closed when the donation is ready -> reason says closed
    def test_closed_recipient_reason(self):
        donations = [make_donation("D-01", quantity=10, ready_time=500, expiry_time=700)]
        recipient = make_recipient("R-01", capacity=50)
        recipient["closing_time"] = 400
        volunteers = [make_volunteer("V-01", vehicle_capacity=30, max_pickups=2)]

        assignments, unassigned = greedy.greedySchedule(donations, [recipient], volunteers)

        self.assertEqual(assignments, [])
        self.assertEqual(unassigned[0]["status"], "unassigned")
        self.assertIn("closed", unassigned[0]["reason"])

    # Volunteer not available at the ready time -> reason says so
    def test_unavailable_volunteer_reason(self):
        donations = [make_donation("D-01", quantity=10, ready_time=500, expiry_time=700)]
        recipients = [make_recipient("R-01", capacity=50)]
        volunteer = make_volunteer("V-01", vehicle_capacity=30, max_pickups=2)
        volunteer["available_to"] = 100

        assignments, unassigned = greedy.greedySchedule(donations, recipients, [volunteer])

        self.assertEqual(assignments, [])
        self.assertEqual(unassigned[0]["status"], "unassigned")
        # the generic fallback says "no available volunteer could take", so check wording only the specific reason has
        self.assertIn("available at the time", unassigned[0]["reason"])
        self.assertIn("ready for pickup", unassigned[0]["reason"])

    # Assigned reason explains why the match works
    def test_assigned_reason_explains_the_match(self):
        donations = [make_donation("D-01", quantity=10, ready_time=0, expiry_time=90)]
        assignments, _ = greedy.greedySchedule(donations, roomy_recipients(), roomy_volunteers())

        reason = assignments[0]["reason"]
        self.assertIn("shelf life: 90", reason)
        self.assertIn("prepared_meals", reason)
        self.assertIn("V-01", reason)

    # No donations at all -> empty results, no crash
    def test_empty_donations(self):
        assignments, unassigned = greedy.greedySchedule([], roomy_recipients(), roomy_volunteers())
        self.assertEqual((assignments, unassigned), ([], []))

    # No recipients at all -> no crash, donation unassigned
    def test_empty_recipients(self):
        donations = [make_donation("D-01", quantity=10, ready_time=0, expiry_time=100)]
        assignments, unassigned = greedy.greedySchedule(donations, [], roomy_volunteers())
        self.assertEqual(assignments, [])
        self.assertEqual(ids(unassigned), ["D-01"])

    # No volunteers at all -> no crash, donation unassigned
    def test_empty_volunteers(self):
        donations = [make_donation("D-01", quantity=10, ready_time=0, expiry_time=100)]
        assignments, unassigned = greedy.greedySchedule(donations, roomy_recipients(), [])
        self.assertEqual(assignments, [])
        self.assertEqual(ids(unassigned), ["D-01"])


class TestFifoVsGreedy(unittest.TestCase):

    # Same input, FIFO and greedy assign different donations (rubric case)
    def test_fifo_and_greedy_produce_different_results(self):
        results = cs.run_both(*cs.contention_scenario())

        self.assertEqual(sorted(ids(results["fifo"]["assignments"])), ["D-101", "D-102"])
        self.assertEqual(sorted(ids(results["greedy"]["assignments"])), ["D-102", "D-103"])
        self.assertEqual(cs.differing_donations(results), ["D-101", "D-103"])
        self.assertEqual(results["fifo"]["metrics"]["quantity_rescued"], 40)
        self.assertEqual(results["greedy"]["metrics"]["quantity_rescued"], 60)

    # Fairness / starvation case: the small non-urgent donation that arrived first is deferred
    def test_starvation_case_defers_the_small_early_donation(self):
        results = cs.run_both(*cs.contention_scenario())

        fifo = cs.outcome_by_id(results["fifo"])
        greedy_outcome = cs.outcome_by_id(results["greedy"])

        self.assertEqual(fifo["D-101"][0], "assigned")
        self.assertEqual(greedy_outcome["D-101"][0], "deferred")
        self.assertIn("D-102", greedy_outcome["D-101"][1])
        self.assertIn("D-103", greedy_outcome["D-101"][1])

    # Greedy can assign FEWER donations: it saves the urgent one but loses two smaller ones
    def test_tradeoff_fifo_assigns_more_greedy_saves_the_urgent_one(self):
        results = cs.run_both(*cs.tradeoff_scenario())
        fifo = results["fifo"]["metrics"]
        greedy_metrics = results["greedy"]["metrics"]

        self.assertEqual(fifo["donations_assigned"], 2)
        self.assertEqual(greedy_metrics["donations_assigned"], 1)
        self.assertEqual(fifo["quantity_rescued"], greedy_metrics["quantity_rescued"])
        self.assertEqual(fifo["urgent_rate"], 0.0)
        self.assertEqual(greedy_metrics["urgent_rate"], 100.0)

    # Both strategies are measured with the same set of metrics
    def test_both_strategies_report_the_same_metrics(self):
        results = cs.run_both(*cs.contention_scenario())
        self.assertEqual(
            sorted(results["fifo"]["metrics"]), sorted(results["greedy"]["metrics"])
        )
        for key in cs.REPORT_METRICS:
            self.assertIn(key, results["fifo"]["metrics"])

    # On the sample files both strategies assign the same donations
    def test_sample_data_assigns_the_same_donations(self):
        results = cs.run_both(*cs.sample_data())
        self.assertEqual(
            sorted(ids(results["fifo"]["assignments"])),
            sorted(ids(results["greedy"]["assignments"])),
        )
        self.assertEqual(cs.differing_donations(results), [])

    # The plain-language takeaway matches the numbers
    def test_summary_lines_match_the_numbers(self):
        results = cs.run_both(*cs.contention_scenario())
        text = " ".join(cs.summary_lines(results))
        self.assertIn("Greedy rescued 20 more units", text)

    # The report prints without crashing and includes the metric table
    def test_report_prints(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cs.print_comparison("Test", "", *cs.contention_scenario())
        output = buffer.getvalue()
        self.assertIn("Metric", output)
        self.assertIn("quantity_rescued", output)


if __name__ == "__main__":
    unittest.main()

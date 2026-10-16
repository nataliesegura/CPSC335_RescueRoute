import unittest

from rr_fifo import fifo_schedule
from rr_greedy import greedySchedule, computeExpandedMetrics

class TestComparison(unittest.TestCase):

    def setUp(self):
        # Two donations competing for limited capacity.
        # D-01 arrives first but has a longer shelf life.
        # D-02 is more urgent.

        self.donations = [
            {
                "donation_id": "D-01",
                "donor_name": "Restaurant A",
                "food_type": "prepared_meals",
                "quantity": 40,
                "ready_time": 0,
                "expiry_time": 300,
                "pickup_area": "Fullerton"
            },
            {
                "donation_id": "D-02",
                "donor_name": "Restaurant B",
                "food_type": "prepared_meals",
                "quantity": 30,
                "ready_time": 10,
                "expiry_time": 70,
                "pickup_area": "Fullerton"
            }
        ]

        self.recipients = [
            {
                "recipient_id": "R-01",
                "org_name": "Test Shelter",
                "accepted_food_types": {"prepared_meals"},
                "capacity": 50,
                "area": "Fullerton",
                "closing_time": 600
            }
        ]

        self.volunteers = [
            {
                "volunteer_id": "V-01",
                "vehicle_capacity": 50,
                "area": "Fullerton",
                "available_from": 0,
                "available_to": 600,
                "max_pickups": 2
            }
        ]

    def test_different_assignments(self):

        fifo_assigned, fifo_unassigned = fifo_schedule(
            self.donations,
            self.recipients,
            self.volunteers
        )

        greedy_assigned, greedy_unassigned = greedySchedule(
            self.donations,
            self.recipients,
            self.volunteers
        )

        # FIFO processes D-01 first.
        self.assertEqual(
            fifo_assigned[0]["donation_id"], "D-01"
        )

        # Greedy prioritizes shorter shelf life.
        self.assertEqual(
            greedy_assigned[0]["donation_id"], "D-02"
        )

        # Verify the rejected donations differ.
        self.assertEqual(
            fifo_unassigned[0]["donation_id"], "D-02"
        )

        self.assertEqual(
            greedy_unassigned[0]["donation_id"], "D-01"
        )

    def test_different_rescue_metrics(self):

        fifo_assigned, fifo_unassigned = fifo_schedule(
            self.donations,
            self.recipients,
            self.volunteers
        )

        greedy_assigned, greedy_unassigned = greedySchedule(
            self.donations,
            self.recipients,
            self.volunteers
        )

        fifo_metrics = computeExpandedMetrics(
            self.donations,
            self.recipients,
            self.volunteers,
            fifo_assigned,
            fifo_unassigned
        )

        greedy_metrics = computeExpandedMetrics(
            self.donations,
            self.recipients,
            self.volunteers,
            greedy_assigned,
            greedy_unassigned
        )

        # FIFO rescues more total food.
        self.assertEqual(
            fifo_metrics["quantity_rescued"], 40
        )

        self.assertEqual(
            greedy_metrics["quantity_rescued"], 30
        )

        # Greedy rescues the more urgent donation.
        self.assertEqual(
            fifo_metrics["urgent_rate"], 0.0
        )

        self.assertEqual(
            greedy_metrics["urgent_rate"], 100.0
        )


if __name__ == "__main__":
    unittest.main()

import unittest
from rr_greedy import *


def makeRecipient(recipient_id="R-01", food_types=None, capacity=50, area="Fullerton"):
    return {
        "recipient_id": recipient_id,
        "org_name": "Test Shelter",
        "accepted_food_types": food_types or {"prepared_meals"},
        "capacity": capacity,
        "area": area,
        "closing_time": 600,
    }

def makeVolunteer(volunteer_id="V-01", vehicle_capacity=30, area="Fullerton", max_pickups=2):
    return {
        "volunteer_id": volunteer_id,
        "vehicle_capacity": vehicle_capacity,
        "area": area,
        "available_from": 0,
        "available_to": 600,
        "max_pickups": max_pickups,
    }

def makeDonation(donation_id="D-01", food_type="prepared_meals", quantity=10,
                  ready_time=0, expiry_time=100, area="Fullerton"):
    return {
        "donation_id": donation_id,
        "donor_name": "Test Donor",
        "food_type": food_type,
        "quantity": quantity,
        "ready_time": ready_time,
        "expiry_time": expiry_time,
        "pickup_area": area,
    }

class TestGreedy(unittest.TestCase):

    def testGreedyPriorities(self):
        # D-01 arrives first but expires late and D-02 arrives later but expires soon.
        donations = [
            makeDonation("D-01", quantity=20, ready_time=0, expiry_time=500),
            makeDonation("D-02", quantity=20, ready_time=10, expiry_time=30),
        ]
        recipients = [makeRecipient(capacity=20)]  # Room for only one
        volunteers = [makeVolunteer(vehicle_capacity=50)]

        assignments, unassigned = greedySchedule(donations, recipients, volunteers)

        self.assertEqual(len(assignments), 1)
        # should pick D-02 because it expires faster
        self.assertEqual(assignments[0]["donation_id"], "D-02")
        self.assertEqual(unassigned[0]["donation_id"], "D-01")

    def testGreedyNormal(self):
        donations = [makeDonation(quantity=10)]
        recipients = [makeRecipient(capacity=50)]
        volunteers = [makeVolunteer(vehicle_capacity=30)]

        assignments, unassigned = greedySchedule(donations, recipients, volunteers)
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]["donation_id"], "D-01")

    def testExpandedMetrics(self):
        donations = [makeDonation("D-01", quantity=10)]
        recipients = [makeRecipient(capacity=50)]
        volunteers = [makeVolunteer(vehicle_capacity=30)]

        assignments, unassigned = greedySchedule(donations, recipients, volunteers)
        metrics = computeExpandedMetrics(donations, recipients, volunteers, assignments, unassigned)

        self.assertEqual(metrics["donations_received"], 1)
        self.assertEqual(metrics["quantity_rescued"], 10)
        self.assertIn("recipient_capacity_utilization_pct", metrics)


if __name__ == "__main__":
    unittest.main()
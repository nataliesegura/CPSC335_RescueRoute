import unittest
from rr_fifo import (
    validate_donations,
    validate_recipients,
    validate_volunteers,
    fifo_schedule,
    compute_metrics,
)


def make_recipient(recipient_id="R-01", food_types=None, capacity=50, area="Fullerton"):
    return {
        "recipient_id": recipient_id,
        "org_name": "Test Shelter",
        "accepted_food_types": food_types or {"prepared_meals"},
        "capacity": capacity,
        "area": area,
        "closing_time": 600,
    }


def make_volunteer(volunteer_id="V-01", vehicle_capacity=30, area="Fullerton", max_pickups=2):
    return {
        "volunteer_id": volunteer_id,
        "vehicle_capacity": vehicle_capacity,
        "area": area,
        "available_from": 0,
        "available_to": 600,
        "max_pickups": max_pickups,
    }


def make_donation(donation_id="D-01", food_type="prepared_meals", quantity=10,
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


class TestValidation(unittest.TestCase):

    # Duplicate donation ID is rejected
    def test_duplicate_donation_id_raises(self):
        donations = [make_donation("D-01"), make_donation("D-01")]
        with self.assertRaises(ValueError):
            validate_donations(donations)

    # ready_time at or after expiry_time is rejected
    def test_bad_time_range_raises(self):
        donations = [make_donation("D-01", ready_time=100, expiry_time=50)]
        with self.assertRaises(ValueError):
            validate_donations(donations)

    # Negative quantity is rejected
    def test_negative_quantity_raises(self):
        donations = [make_donation("D-01", quantity=-5)]
        with self.assertRaises(ValueError):
            validate_donations(donations)

    # Normal, valid donations pass validation without raising
    def test_valid_donations_pass(self):
        donations = [make_donation("D-01"), make_donation("D-02")]
        self.assertTrue(validate_donations(donations))

    # Equal ready/expiry times = already expired, rejected
    def test_already_expired_donation_raises(self):
        donations = [make_donation("D-01", ready_time=50, expiry_time=50)]
        with self.assertRaises(ValueError):
            validate_donations(donations)

    # Duplicate recipient ID is rejected
    def test_duplicate_recipient_id_raises(self):
        recipients = [make_recipient("R-01"), make_recipient("R-01")]
        with self.assertRaises(ValueError):
            validate_recipients(recipients)

    # Duplicate volunteer ID is rejected
    def test_duplicate_volunteer_id_raises(self):
        volunteers = [make_volunteer("V-01"), make_volunteer("V-01")]
        with self.assertRaises(ValueError):
            validate_volunteers(volunteers)


class TestFifoSchedule(unittest.TestCase):

    # Fully compatible donation gets assigned to the right recipient + volunteer
    def test_normal_match_is_assigned(self):
        donations = [make_donation(quantity=10)]
        recipients = [make_recipient(capacity=50)]
        volunteers = [make_volunteer(vehicle_capacity=30)]

        assignments, unassigned = fifo_schedule(donations, recipients, volunteers)

        self.assertEqual(len(assignments), 1)
        self.assertEqual(len(unassigned), 0)
        self.assertEqual(assignments[0]["recipient_id"], "R-01")
        self.assertEqual(assignments[0]["volunteer_id"], "V-01")

    # No recipient accepts the food type -> unassigned, reason says so
    def test_incompatible_food_type_is_unassigned(self):
        donations = [make_donation(food_type="produce")]
        recipients = [make_recipient(food_types={"prepared_meals"})]
        volunteers = [make_volunteer()]

        assignments, unassigned = fifo_schedule(donations, recipients, volunteers)

        self.assertEqual(len(assignments), 0)
        self.assertEqual(len(unassigned), 1)
        self.assertIn("no compatible recipient", unassigned[0]["reason"].lower())

    # Donation too large for any recipient's capacity -> unassigned
    def test_insufficient_recipient_capacity_is_unassigned(self):
        donations = [make_donation(quantity=100)]
        recipients = [make_recipient(capacity=50)]
        volunteers = [make_volunteer(vehicle_capacity=100)]

        assignments, unassigned = fifo_schedule(donations, recipients, volunteers)

        self.assertEqual(len(assignments), 0)
        self.assertEqual(len(unassigned), 1)

    # Recipient fits, but no volunteer has enough vehicle capacity -> unassigned
    def test_no_volunteer_capacity_is_unassigned(self):
        donations = [make_donation(quantity=40)]
        recipients = [make_recipient(capacity=50)]
        volunteers = [make_volunteer(vehicle_capacity=10)]  # too small

        assignments, unassigned = fifo_schedule(donations, recipients, volunteers)

        self.assertEqual(len(assignments), 0)
        self.assertEqual(len(unassigned), 1)
        self.assertIn("volunteer", unassigned[0]["reason"].lower())

    # Two donations, one recipient with room for only one -> FIFO order wins
    def test_two_donations_compete_for_same_capacity(self):
        donations = [make_donation("D-01", quantity=30), make_donation("D-02", quantity=30)]
        recipients = [make_recipient(capacity=30)]
        volunteers = [make_volunteer(vehicle_capacity=50, max_pickups=2)]

        assignments, unassigned = fifo_schedule(donations, recipients, volunteers)

        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]["donation_id"], "D-01")
        self.assertEqual(len(unassigned), 1)
        self.assertEqual(unassigned[0]["donation_id"], "D-02")

    # No donations at all -> empty results, no crash
    def test_empty_input_produces_empty_output(self):
        assignments, unassigned = fifo_schedule([], [make_recipient()], [make_volunteer()])
        self.assertEqual(assignments, [])
        self.assertEqual(unassigned, [])

    # Tight but valid window still matches correctly
    def test_near_expiry_donation_still_matches(self):
        donations = [make_donation(ready_time=0, expiry_time=1)]
        recipients = [make_recipient(capacity=50)]
        volunteers = [make_volunteer(vehicle_capacity=30)]

        assignments, unassigned = fifo_schedule(donations, recipients, volunteers)

        self.assertEqual(len(assignments), 1)
        self.assertEqual(len(unassigned), 0)

    # No recipients at all -> no crash, donation unassigned
    def test_empty_recipients_list_is_unassigned(self):
        donations = [make_donation()]
        assignments, unassigned = fifo_schedule(donations, [], [make_volunteer()])

        self.assertEqual(assignments, [])
        self.assertEqual(len(unassigned), 1)
        self.assertEqual(unassigned[0]["donation_id"], "D-01")

    # No volunteers at all -> no crash, unassigned, reason blames volunteer stage
    def test_empty_volunteers_list_is_unassigned(self):
        donations = [make_donation()]
        recipients = [make_recipient(capacity=50)]
        assignments, unassigned = fifo_schedule(donations, recipients, [])

        self.assertEqual(assignments, [])
        self.assertEqual(len(unassigned), 1)
        self.assertEqual(unassigned[0]["donation_id"], "D-01")
        self.assertIn("volunteer", unassigned[0]["reason"].lower())


class TestMetrics(unittest.TestCase):

    # Metrics (received/assigned/unassigned/rescued/at-risk) match hand-calculated values
    def test_metrics_add_up(self):
        donations = [make_donation("D-01", quantity=10), make_donation("D-02", quantity=20)]
        recipients = [make_recipient(capacity=10)]
        volunteers = [make_volunteer(vehicle_capacity=30)]

        assignments, unassigned = fifo_schedule(donations, recipients, volunteers)
        metrics = compute_metrics(donations, assignments, unassigned)

        self.assertEqual(metrics["donations_received"], 2)
        self.assertEqual(metrics["donations_assigned"], 1)
        self.assertEqual(metrics["donations_unassigned"], 1)
        self.assertEqual(metrics["quantity_rescued"], 10)
        self.assertEqual(metrics["quantity_at_risk"], 20)


if __name__ == "__main__":
    unittest.main()

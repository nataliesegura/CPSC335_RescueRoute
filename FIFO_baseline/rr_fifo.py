import json

# Loading data from JSON files
# Each file is just a JSON array of objects

def load_donations(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_recipients(path):
    with open(path, encoding="utf-8") as f:
        recipients = json.load(f)
    for recipient in recipients:
        recipient["accepted_food_types"] = set(recipient["accepted_food_types"])
    return recipients


def load_volunteers(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Validation
# Similar setup as Campus_Space
def validate_donations(donations):
    seen_ids = set()
    for donation in donations:
        donation_id = donation["donation_id"]
        if donation_id in seen_ids:
            raise ValueError(f"Duplicate donation ID: {donation_id}")
        seen_ids.add(donation_id)

        if donation["quantity"] <= 0:
            raise ValueError(f"{donation_id}: quantity must be positive")

        if donation["ready_time"] >= donation["expiry_time"]:
            raise ValueError(
                f"{donation_id}: expiry_time must be after ready_time"
            )
    return True


def validate_recipients(recipients):
    seen_ids = set()
    for recipient in recipients:
        recipient_id = recipient["recipient_id"]
        if recipient_id in seen_ids:
            raise ValueError(f"Duplicate recipient ID: {recipient_id}")
        seen_ids.add(recipient_id)

        if recipient["capacity"] < 0:
            raise ValueError(f"{recipient_id}: capacity cannot be negative")
    return True


def validate_volunteers(volunteers):
    seen_ids = set()
    for volunteer in volunteers:
        volunteer_id = volunteer["volunteer_id"]
        if volunteer_id in seen_ids:
            raise ValueError(f"Duplicate volunteer ID: {volunteer_id}")
        seen_ids.add(volunteer_id)

        if volunteer["vehicle_capacity"] <= 0:
            raise ValueError(f"{volunteer_id}: vehicle_capacity must be positive")

        if volunteer["max_pickups"] <= 0:
            raise ValueError(f"{volunteer_id}: max_pickups must be positive")
    return True


# FIFO baseline scheduler
# assignments/unassigned & selected/reject follow the format from Campus_Space
# volunteer search follows the format of Hospital_Dispatch
# remaining_capacity/remaining_pickups follows the format of SwitftServe
def fifo_schedule(donations, recipients, volunteers):
    """
    Process donations in arrival order (the order of the input list).
    For each donation, assign the FIRST feasible recipient and the FIRST
    feasible volunteer. Feasible now also requires the recipient to still
    be open (ready_time before closing_time) and the volunteer to be
    available at ready_time (within available_from/available_to).
    Every donation gets a result, assigned or not.

    Returns (assignments, unassigned) where each is a list of dicts.
    """
    # Track remaining capacity/pickups without mutating the caller's data
    remaining_capacity = {r["recipient_id"]: r["capacity"] for r in recipients}
    remaining_pickups = {v["volunteer_id"]: v["max_pickups"] for v in volunteers}

    assignments = []
    unassigned = []

    for donation in donations:
        chosen_recipient = None
        recipient_was_closed = False
        for recipient in recipients:
            fits_food_type = donation["food_type"] in recipient["accepted_food_types"]
            fits_area = donation["pickup_area"] == recipient["area"]
            fits_capacity = remaining_capacity[recipient["recipient_id"]] >= donation["quantity"]
            fits_time = donation["ready_time"] < recipient["closing_time"]

            if fits_food_type and fits_area and fits_capacity and fits_time:
                chosen_recipient = recipient
                break
            if fits_food_type and fits_area and fits_capacity and not fits_time:
                recipient_was_closed = True

        if chosen_recipient is None:
            if recipient_was_closed:
                reason = (
                    f"A recipient accepted '{donation['food_type']}' and had "
                    f"capacity, but was already closed by the time this "
                    f"donation was ready for pickup."
                )
            else:
                reason = (
                    f"No compatible recipient had room for "
                    f"{donation['quantity']} units of "
                    f"'{donation['food_type']}' in {donation['pickup_area']} "
                    f"before it needed to be picked up."
                )
            unassigned.append({
                "donation_id": donation["donation_id"],
                "status": "unassigned",
                "reason": reason,
            })
            continue

        chosen_volunteer = None
        volunteer_unavailable = False
        for volunteer in volunteers:
            fits_area = donation["pickup_area"] == volunteer["area"]
            fits_vehicle = volunteer["vehicle_capacity"] >= donation["quantity"]
            has_pickups_left = remaining_pickups[volunteer["volunteer_id"]] > 0
            fits_availability = (
                volunteer["available_from"] <= donation["ready_time"] <= volunteer["available_to"]
            )

            if fits_area and fits_vehicle and has_pickups_left and fits_availability:
                chosen_volunteer = volunteer
                break
            if fits_area and fits_vehicle and has_pickups_left and not fits_availability:
                volunteer_unavailable = True

        if chosen_volunteer is None:
            if volunteer_unavailable:
                reason = (
                    f"A compatible recipient ({chosen_recipient['org_name']}) "
                    f"had room, but no volunteer in {donation['pickup_area']} "
                    f"was available at the donation's ready time."
                )
            else:
                reason = (
                    f"A compatible recipient ({chosen_recipient['org_name']}) "
                    f"had room, but no volunteer in {donation['pickup_area']} "
                    f"had enough vehicle capacity or pickups remaining."
                )
            unassigned.append({
                "donation_id": donation["donation_id"],
                "status": "unassigned",
                "reason": reason,
            })
            continue

        # Commit the match: reduce remaining capacity/pickups
        remaining_capacity[chosen_recipient["recipient_id"]] -= donation["quantity"]
        remaining_pickups[chosen_volunteer["volunteer_id"]] -= 1

        assignments.append({
            "donation_id": donation["donation_id"],
            "recipient_id": chosen_recipient["recipient_id"],
            "volunteer_id": chosen_volunteer["volunteer_id"],
            "status": "assigned",
            "reason": (
                f"Assigned to {chosen_recipient['org_name']} with volunteer "
                f"{chosen_volunteer['volunteer_id']}: accepts "
                f"'{donation['food_type']}', had capacity for "
                f"{donation['quantity']} units, was open, and the volunteer "
                f"was available to carry the quantity in "
                f"{donation['pickup_area']}."
            ),
        })

    return assignments, unassigned


# Metrics
# compute_metrics follows the format of peak_find_algo

def compute_metrics(donations, assignments, unassigned):
    quantity_by_id = {d["donation_id"]: d["quantity"] for d in donations}

    quantity_rescued = sum(quantity_by_id[a["donation_id"]] for a in assignments)
    quantity_at_risk = sum(quantity_by_id[u["donation_id"]] for u in unassigned)

    return {
        "donations_received": len(donations),
        "donations_assigned": len(assignments),
        "donations_unassigned": len(unassigned),
        "quantity_rescued": quantity_rescued,
        "quantity_at_risk": quantity_at_risk,
    }


# ---------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------

if __name__ == "__main__":
    donations = load_donations("sample_donations.json")
    recipients = load_recipients("sample_recipients.json")
    volunteers = load_volunteers("sample_volunteers.json")

    validate_donations(donations)
    validate_recipients(recipients)
    validate_volunteers(volunteers)

    print("--- RescueRoute: FIFO Baseline ---")
    assignments, unassigned = fifo_schedule(donations, recipients, volunteers)

    print("\nAssigned:")
    for a in assignments:
        print(f"  {a['donation_id']}: {a['reason']}")

    print("\nUnassigned:")
    for u in unassigned:
        print(f"  {u['donation_id']}: {u['reason']}")

    metrics = compute_metrics(donations, assignments, unassigned)
    print("\n--- Metrics ---")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

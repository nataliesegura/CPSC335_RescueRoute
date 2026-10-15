import json

# file loaders:
def loadDonations(path):
    with open(path, encoding="utf-8") as e:
        return json.load(e)

def loadRecipients(path):
    with open(path, encoding="utf-8") as e:
        recipients = json.load(e)
    for recipient in recipients:
        recipient["accepted_food_types"] = set(recipient["accepted_food_types"])
    return recipients

def loadVolunteers(path):
    with open(path, encoding="utf-8") as e:
        return json.load(e)


# validators:
def validateDonations(donations):
    seen_ids = set()
    for donation in donations:
        donation_id = donation["donation_id"]
        if donation_id in seen_ids:
            raise ValueError(f"duplicate donation ID: {donation_id}")
        seen_ids.add(donation_id)

        if donation["quantity"] <= 0:
            raise ValueError(f"{donation_id}: quantity must be positive")

        if donation["ready_time"] >= donation["expiry_time"]:
            raise ValueError(f"{donation_id}: expiry_time must be after ready_time")
    return True


def validateRecipients(recipients):
    seen_ids = set()
    for recipient in recipients:
        recipient_id = recipient["recipient_id"]
        if recipient_id in seen_ids:
            raise ValueError(f"duplicate recipient ID: {recipient_id}")
        seen_ids.add(recipient_id)

        if recipient["capacity"] < 0:
            raise ValueError(f"{recipient_id}: capacity can't be negative")
    return True


def validateVolunteers(volunteers):
    seen_ids = set()
    for volunteer in volunteers:
        volunteer_id = volunteer["volunteer_id"]
        if volunteer_id in seen_ids:
            raise ValueError(f"duplicate volunteer ID: {volunteer_id}")
        seen_ids.add(volunteer_id)

        if volunteer["vehicle_capacity"] <= 0:
            raise ValueError(f"{volunteer_id}: vehicle_capacity must be positive")

        if volunteer["max_pickups"] <= 0:
            raise ValueError(f"{volunteer_id}: max_pickups must be positive")
    return True


# main function
def greedySchedule(donations, recipients, volunteers):
    # sorts donations by urgency(shortest remaining shelf life first), then quantity(largest first), then arrival time.
    # then assigns recipients and volunteers.

    remaining_capacity = {r["recipient_id"]: r["capacity"] for r in recipients}
    remaining_pickups = {v["volunteer_id"]: v["max_pickups"] for v in volunteers}

    assignments = []
    unassigned = []

    sorted_donations = sorted(donations, key=lambda d: ((d["expiry_time"] - d["ready_time"]), -d["quantity"], d["ready_time"]))

    for donation in sorted_donations:
        chosen_recipient = None
        for recipient in recipients:
            fits_food = donation["food_type"] in recipient["accepted_food_types"]
            fits_area = donation["pickup_area"] == recipient["area"]
            fits_cap = remaining_capacity[recipient["recipient_id"]] >= donation["quantity"]
            scheduled_time = donation["ready_time"]
            fits_time = (
                scheduled_time < donation["expiry_time"]
                and scheduled_time < recipient["closing_time"]
            )

            if fits_food and fits_area and fits_cap and fits_time:
                chosen_recipient = recipient
                break

        if chosen_recipient is None:
            unassigned.append({
                "donation_id": donation["donation_id"],
                "status": "unassigned",
                "reason": f"no compatible and open recipient had enough room for {donation['donation_id']}."
            })
            continue

        chosen_volunteer = None
        for volunteer in volunteers:
            fits_area = donation["pickup_area"] == volunteer["area"]
            fits_vehicle = volunteer["vehicle_capacity"] >= donation["quantity"]
            has_pickups = remaining_pickups[volunteer["volunteer_id"]] > 0
            fits_availability = volunteer["available_from"] <= donation["ready_time"] <= volunteer["available_to"]

            if fits_area and fits_vehicle and has_pickups and fits_availability:
                chosen_volunteer = volunteer
                break

        if chosen_volunteer is None:
            unassigned.append({
                "donation_id": donation["donation_id"],
                "status": "unassigned",
                "reason": f"recipient found, but no available volunteer could take {donation['donation_id']}."
            })
            continue

        # update the remaining capacity and pickups
        remaining_capacity[chosen_recipient["recipient_id"]] -= donation["quantity"]
        remaining_pickups[chosen_volunteer["volunteer_id"]] -= 1

        shelf_life = donation["expiry_time"] - donation["ready_time"]
        assignments.append({
            "donation_id": donation["donation_id"],
            "recipient_id": chosen_recipient["recipient_id"],
            "volunteer_id": chosen_volunteer["volunteer_id"],
            "scheduled_time": donation["ready_time"],
            "status": "assigned",
            "reason": f"assigned by greedy rule (shelf life: {shelf_life} mins) to {chosen_recipient['org_name']} with {chosen_volunteer['volunteer_id']}."
        })

    return assignments, unassigned


# metrics things
def computeExpandedMetrics(donations, recipients, volunteers, assignments, unassigned):
    quantity_by_id = {d["donation_id"]: d["quantity"] for d in donations}
    
    rescued = sum(quantity_by_id[a["donation_id"]] for a in assignments)
    at_risk = sum(quantity_by_id[u["donation_id"]] for u in unassigned)
    
    total_recip_cap = sum(r["capacity"] for r in recipients)
    recip_util = (rescued / total_recip_cap * 100) if total_recip_cap > 0 else 0.0

    total_vol_cap = sum(v["vehicle_capacity"] * v["max_pickups"] for v in volunteers)
    vol_util = (rescued / total_vol_cap * 100) if total_vol_cap > 0 else 0.0

    urgent_donations = [
        d for d in donations
        if 0 < (d["expiry_time"] - d["ready_time"]) <= 120
    ]

    assigned_ids = {a["donation_id"] for a in assignments}

    urgent_assigned = sum(
        1 for d in urgent_donations
        if d["donation_id"] in assigned_ids
    )

    urgent_rate = (
        urgent_assigned / len(urgent_donations) * 100
        if urgent_donations else 0.0
    )

    return {
        "donations_received": len(donations),
        "donations_assigned": len(assignments),
        "donations_unassigned": len(unassigned),
        "quantity_rescued": rescued,
        "quantity_at_risk": at_risk,
        "recipient_capacity_utilization_pct": round(recip_util, 2),
        "volunteer_capacity_utilization_pct": round(vol_util, 2),
        "urgent_rate": round(urgent_rate, 2),
    }


if __name__ == "__main__":
    donations = loadDonations("../FIFO_baseline/sample_donations.json")
    recipients = loadRecipients("../FIFO_baseline/sample_recipients.json")
    volunteers = loadVolunteers("../FIFO_baseline/sample_volunteers.json")

    validateDonations(donations)
    validateRecipients(recipients)
    validateVolunteers(volunteers)

    assignments, unassigned = greedySchedule(donations, recipients, volunteers)
    
    metrics = computeExpandedMetrics(
        donations,
        recipients,
        volunteers,
        assignments,
        unassigned
    )
    
    print("\nGreedy Assignments:", len(assignments))
    print("Greedy Unassigned:", len(unassigned))

    print("\nGreedy Performance Metrics")
    print("-" * 45)

    for metric, value in metrics.items():
        print(f"{metric}: {value}")
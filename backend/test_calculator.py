"""Unit tests for the deterministic calculator. Runs without Claude/credits."""

import calculator


def _restaurant_extraction():
    return {
        "people": ["Akhilesh", "Kritik", "Rujula", "Dhruv", "Shobhit"],
        "items": [
            {"label": "Veg food", "total": 1300, "sharedBy": ["Dhruv", "Kritik"],
             "category": "veg", "split": "equal"},
            {"label": "Veg + non-veg food", "total": 2200,
             "sharedBy": ["Akhilesh", "Rujula", "Shobhit"], "category": "nonveg",
             "split": "equal"},
            {"label": "Beer (Kritik)", "total": 400, "sharedBy": ["Kritik"],
             "category": "drinks", "split": "equal"},
            {"label": "Beer (Shobhit)", "total": 400, "sharedBy": ["Shobhit"],
             "category": "drinks", "split": "equal"},
            {"label": "Tax", "total": 600,
             "sharedBy": ["Akhilesh", "Kritik", "Rujula", "Dhruv", "Shobhit"],
             "category": "tax", "split": "proportional"},
        ],
        "assumptions": ["veg-only diners are Dhruv and Kritik"],
        "oneLiner": "Proportional tax by food share.",
    }


def test_restaurant_balances_and_is_correct():
    # Tax (600) is split EQUALLY: 120 each. Food shares differ by what each ate.
    r = calculator.compute_split(_restaurant_extraction())
    assert r["totalBill"] == 4900
    assert sum(r["perPerson"].values()) == 4900, r["perPerson"]
    pp = r["perPerson"]
    # Veg-only diners: own veg share (650) + equal tax (120), + beer for Kritik.
    assert pp["Dhruv"] == 770          # 650 + 120
    assert pp["Kritik"] == 1170        # 650 + 400 beer + 120
    # Veg+nonveg trio: ~733 food + 120 tax (±1 rounding on the tied food share).
    assert pp["Akhilesh"] in (853, 854)
    assert pp["Rujula"] in (853, 854)
    assert pp["Shobhit"] in (1253, 1254)  # + own beer 400
    # Veg-only diners pay LESS than the veg+nonveg trio (smaller food, equal tax).
    assert pp["Dhruv"] < pp["Akhilesh"] and pp["Kritik"] < pp["Shobhit"]


def test_single_equal_item_splits_evenly():
    r = calculator.compute_split({
        "people": ["A", "B", "C"],
        "items": [{"label": "Lunch", "total": 90, "sharedBy": ["A", "B", "C"],
                   "category": "other", "split": "equal"}],
        "assumptions": [], "oneLiner": "",
    })
    assert r["totalBill"] == 90
    assert r["perPerson"] == {"A": 30, "B": 30, "C": 30}


def test_rounding_reconciles_to_total():
    # 100 / 3 = 33.33 each → must still sum to 100.
    r = calculator.compute_split({
        "people": ["A", "B", "C"],
        "items": [{"label": "X", "total": 100, "sharedBy": ["A", "B", "C"],
                   "category": "other", "split": "equal"}],
        "assumptions": [], "oneLiner": "",
    })
    assert sum(r["perPerson"].values()) == 100
    assert sorted(r["perPerson"].values()) == [33, 33, 34]


def test_fixed_tax_splits_equally():
    # A fixed tax/service amount is split equally among the people it applies to.
    r = calculator.compute_split({
        "people": ["A", "B", "C"],
        "items": [
            {"label": "Food", "total": 900, "sharedBy": ["A", "B"],
             "category": "nonveg", "split": "equal"},
            {"label": "Side", "total": 300, "sharedBy": ["C"],
             "category": "nonveg", "split": "equal"},
            {"label": "Service", "total": 120, "sharedBy": ["A", "B", "C"],
             "category": "tax", "split": "proportional"},
        ],
        "assumptions": [], "oneLiner": "",
    })
    # Service 120 split equally = 40 each (NOT weighted by the 450/450/300 food spend).
    assert r["totalBill"] == 1320
    assert r["perPerson"] == {"A": 490, "B": 490, "C": 340}


def test_single_payer():
    r = calculator.compute_split({
        "people": ["Karan", "Neha", "Priya"],
        "items": [{"label": "Lunch", "total": 4500,
                   "sharedBy": ["Karan", "Neha", "Priya"], "category": "other",
                   "split": "equal"}],
        "assumptions": [], "oneLiner": "",
    })
    assert sum(r["perPerson"].values()) == 4500
    assert r["perPerson"]["Karan"] == 1500


def test_tax_equally_correction_path():
    # Same bill but tax marked "equal" (as a rule-changing correction would do).
    extraction = _restaurant_extraction()
    extraction["items"][-1]["split"] = "equal"
    r = calculator.compute_split(extraction)
    assert sum(r["perPerson"].values()) == 4900
    # Equal tax = 120 each; veg-only Dhruv = 650 + 120 = 770.
    assert r["perPerson"]["Dhruv"] == 770


def test_people_inferred_from_items_when_missing():
    r = calculator.compute_split({
        "items": [{"label": "X", "total": 100, "sharedBy": ["A", "B"],
                   "category": "other", "split": "equal"}],
        "assumptions": [], "oneLiner": "",
    })
    assert set(r["people"]) == {"A", "B"}


def test_single_payer_settlement():
    r = calculator.compute_split({
        "people": ["Karan", "Neha", "Priya"],
        "items": [{"label": "Lunch", "total": 4500,
                   "sharedBy": ["Karan", "Neha", "Priya"], "category": "other",
                   "split": "equal", "payer": "Karan"}],
        "assumptions": [], "oneLiner": "",
    })
    assert r["paidBy"] == {"Karan": 4500}
    s = r["settlements"]
    # Both others owe Karan their ₹1500 share; ≤ n-1 transactions.
    assert {(t["from"], t["to"], t["amount"]) for t in s} == {
        ("Neha", "Karan", 1500), ("Priya", "Karan", 1500),
    }
    assert len(s) <= len(r["people"]) - 1


def test_two_payers_different_items_nets_to_zero():
    # A fronted the activity, B fronted the snacks — both shared by all four.
    r = calculator.compute_split({
        "people": ["A", "B", "C", "D"],
        "items": [
            {"label": "Activity", "total": 3000, "sharedBy": ["A", "B", "C", "D"],
             "category": "other", "split": "equal", "payer": "A"},
            {"label": "Snacks", "total": 1000, "sharedBy": ["A", "B", "C", "D"],
             "category": "other", "split": "equal", "payer": "B"},
        ],
        "assumptions": [], "oneLiner": "",
    })
    assert r["paidBy"] == {"A": 3000, "B": 1000}
    bal = {p: 0 for p in r["people"]}
    for t in r["settlements"]:
        bal[t["from"]] -= t["amount"]
        bal[t["to"]] += t["amount"]
    # Each owes 1000: A net +2000, B net 0, C/D net -1000.
    assert bal == {"A": 2000, "B": 0, "C": -1000, "D": -1000}


def test_self_paid_means_no_settlements():
    r = calculator.compute_split({
        "people": ["A", "B"],
        "items": [{"label": "X", "total": 100, "sharedBy": ["A", "B"],
                   "category": "other", "split": "equal", "payer": "self"}],
        "assumptions": [], "oneLiner": "",
    })
    assert r["settlements"] == []
    assert r["paidBy"] == {}


def test_missing_payer_means_no_settlements():
    # No payer field at all → treated as unknown → shares only.
    r = calculator.compute_split({
        "people": ["A", "B"],
        "items": [{"label": "X", "total": 100, "sharedBy": ["A", "B"],
                   "category": "other", "split": "equal"}],
        "assumptions": [], "oneLiner": "",
    })
    assert r["settlements"] == []


def test_mixed_self_and_group_funded():
    # The real edge case: one group-funded item + per-person self-paid drinks.
    # Only the group item should produce settlements; drinks are already settled.
    r = calculator.compute_split({
        "people": ["A", "B", "C"],
        "items": [
            {"label": "Hotel", "total": 3000, "sharedBy": ["A", "B", "C"],
             "category": "other", "split": "equal", "payer": "A"},
            {"label": "A's drink", "total": 100, "sharedBy": ["A"],
             "category": "drinks", "split": "equal", "payer": "self"},
            {"label": "B's drink", "total": 200, "sharedBy": ["B"],
             "category": "drinks", "split": "equal", "payer": "self"},
        ],
        "assumptions": [], "oneLiner": "",
    })
    assert r["totalBill"] == 3300
    assert sum(r["perPerson"].values()) == 3300
    assert r["paidBy"] == {"A": 3000}  # only the group item
    # Settlement covers only the hotel (1000 each); drinks excluded entirely.
    assert {(t["from"], t["to"], t["amount"]) for t in r["settlements"]} == {
        ("B", "A", 1000), ("C", "A", 1000),
    }


def test_payer_who_ate_nothing_gets_full_amount_back():
    # Boss pays, doesn't eat; two staff split the meal and repay the boss.
    r = calculator.compute_split({
        "people": ["Staff1", "Staff2"],
        "items": [{"label": "Meal", "total": 1000, "sharedBy": ["Staff1", "Staff2"],
                   "category": "other", "split": "equal", "payer": "Boss"}],
        "assumptions": [], "oneLiner": "",
    })
    assert "Boss" in r["people"]
    assert r["perPerson"]["Boss"] == 0
    inflow = sum(t["amount"] for t in r["settlements"] if t["to"] == "Boss")
    assert inflow == 1000


def test_restaurant_with_payer_settles_to_zero():
    extraction = _restaurant_extraction()
    for item in extraction["items"]:
        item["payer"] = "Akhilesh"  # Akhilesh fronted the whole bill
    r = calculator.compute_split(extraction)
    s = r["settlements"]
    bal = {p: 0 for p in r["people"]}
    for t in s:
        bal[t["from"]] -= t["amount"]
        bal[t["to"]] += t["amount"]
    # Akhilesh fronted everything: gets back 4900 − own share.
    assert bal["Akhilesh"] == 4900 - r["perPerson"]["Akhilesh"]
    assert sum(bal.values()) == 0
    assert len(s) <= len(r["people"]) - 1


def test_percentage_gst_computed_and_distributed():
    # 18% GST on a ₹1000 food item shared equally by A and B → ₹180, ₹90 each.
    r = calculator.compute_split({
        "people": ["A", "B"],
        "items": [
            {"label": "Food", "total": 1000, "sharedBy": ["A", "B"],
             "category": "nonveg", "split": "equal", "payer": "self"},
            {"label": "GST", "rate": 0.18, "appliesTo": ["Food"],
             "category": "tax", "payer": "self"},
        ],
        "assumptions": [], "oneLiner": "",
    })
    assert r["totalBill"] == 1180
    assert r["perPerson"] == {"A": 590, "B": 590}


def test_percentage_rate_given_as_whole_number():
    # "18" should be read as 18%, same as 0.18.
    r = calculator.compute_split({
        "people": ["A", "B"],
        "items": [
            {"label": "Food", "total": 1000, "sharedBy": ["A", "B"],
             "category": "nonveg", "split": "equal", "payer": "self"},
            {"label": "Service", "rate": 18, "appliesTo": ["Food"],
             "category": "tax", "payer": "self"},
        ],
        "assumptions": [], "oneLiner": "",
    })
    assert r["totalBill"] == 1180


def test_percentage_excludes_items_not_in_appliesTo():
    # GST applies only to the hotel, not the drinks.
    r = calculator.compute_split({
        "people": ["A", "B"],
        "items": [
            {"label": "Hotel", "total": 1000, "sharedBy": ["A", "B"],
             "category": "other", "split": "equal", "payer": "self"},
            {"label": "Drinks", "total": 500, "sharedBy": ["A", "B"],
             "category": "drinks", "split": "equal", "payer": "self"},
            {"label": "GST", "rate": 0.18, "appliesTo": ["Hotel"],
             "category": "tax", "payer": "self"},
        ],
        "assumptions": [], "oneLiner": "",
    })
    # 18% of 1000 = 180 (NOT on the 500 drinks). Total = 1000 + 500 + 180 = 1680.
    assert r["totalBill"] == 1680
    assert r["perPerson"] == {"A": 840, "B": 840}


def test_percentage_split_equally_among_base_consumers():
    # A used the expensive room and B the cheap one, but GST is split EQUALLY
    # between the two of them (not weighted by room cost).
    r = calculator.compute_split({
        "people": ["A", "B"],
        "items": [
            {"label": "Room A", "total": 3000, "sharedBy": ["A"],
             "category": "other", "split": "equal", "payer": "self"},
            {"label": "Room B", "total": 1000, "sharedBy": ["B"],
             "category": "other", "split": "equal", "payer": "self"},
            {"label": "GST", "rate": 0.10, "appliesTo": ["Room A", "Room B"],
             "category": "tax", "payer": "self"},
        ],
        "assumptions": [], "oneLiner": "",
    })
    # GST = 10% of 4000 = 400, split equally → 200 each → A=3200, B=1200.
    assert r["totalBill"] == 4400
    assert r["perPerson"] == {"A": 3200, "B": 1200}


def test_percentage_with_group_payer_settles():
    # Kritik fronts the whole bill incl. GST; A repays their full share.
    r = calculator.compute_split({
        "people": ["Kritik", "A"],
        "items": [
            {"label": "Food", "total": 1000, "sharedBy": ["Kritik", "A"],
             "category": "nonveg", "split": "equal", "payer": "Kritik"},
            {"label": "GST", "rate": 0.18, "appliesTo": ["Food"],
             "category": "tax", "payer": "Kritik"},
        ],
        "assumptions": [], "oneLiner": "",
    })
    assert r["totalBill"] == 1180
    assert r["paidBy"] == {"Kritik": 1180}
    # A owes half of 1180 = 590, pays it to Kritik.
    assert {(t["from"], t["to"], t["amount"]) for t in r["settlements"]} == {("A", "Kritik", 590)}


def test_covered_share_is_a_gift_no_repayment():
    # A gifts D's share of the dinner. D owes nothing; A bears two shares; self-paid
    # so there is NO settlement debt (it's a gift, not a loan).
    r = calculator.compute_split({
        "people": ["A", "B", "C", "D"],
        "items": [{"label": "Dinner", "total": 4000,
                   "sharedBy": ["A", "B", "C", "D"], "category": "nonveg",
                   "split": "equal", "payer": "self", "coveredBy": {"D": "A"}}],
        "assumptions": [], "oneLiner": "",
    })
    assert r["totalBill"] == 4000
    assert r["perPerson"] == {"A": 2000, "B": 1000, "C": 1000, "D": 0}
    assert r["settlements"] == []  # gift => no repayment


def test_covered_share_with_group_payer_routes_debt_to_giver():
    # C fronted the whole dinner. A gifts B's share. So B owes nothing; A owes
    # B's share too, and repays C for both — no B->anyone transaction.
    r = calculator.compute_split({
        "people": ["A", "B", "C"],
        "items": [{"label": "Dinner", "total": 3000,
                   "sharedBy": ["A", "B", "C"], "category": "nonveg",
                   "split": "equal", "payer": "C", "coveredBy": {"B": "A"}}],
        "assumptions": [], "oneLiner": "",
    })
    assert r["perPerson"] == {"A": 2000, "B": 0, "C": 1000}
    assert r["paidBy"] == {"C": 3000}
    # A owes C for two shares (own + B's gift); B owes nobody.
    assert {(t["from"], t["to"], t["amount"]) for t in r["settlements"]} == {("A", "C", 2000)}
    assert all(t["from"] != "B" for t in r["settlements"])


def test_whole_item_treat():
    # Host treats both guests — everyone consumed, host bears it all, no repayment.
    r = calculator.compute_split({
        "people": ["Host", "G1", "G2"],
        "items": [{"label": "Cake", "total": 900, "sharedBy": ["Host", "G1", "G2"],
                   "category": "other", "split": "equal", "payer": "self",
                   "coveredBy": {"G1": "Host", "G2": "Host"}}],
        "assumptions": [], "oneLiner": "",
    })
    assert r["perPerson"] == {"Host": 900, "G1": 0, "G2": 0}
    assert r["settlements"] == []


def test_detailed_settlements_break_down_by_item():
    # Rohan paid the cab (everyone), Vikram paid desserts (not Rohan).
    r = calculator.compute_split({
        "people": ["Rohan", "Sneha", "Vikram"],
        "items": [
            {"label": "Cab", "total": 900, "sharedBy": ["Rohan", "Sneha", "Vikram"],
             "category": "other", "split": "equal", "payer": "Rohan"},
            {"label": "Desserts", "total": 600, "sharedBy": ["Sneha", "Vikram"],
             "category": "nonveg", "split": "equal", "payer": "Vikram"},
        ],
        "assumptions": [], "oneLiner": "",
    })
    detailed = {(t["from"], t["to"], t["amount"], t["for"]) for t in r["settlementsDetailed"]}
    # Cab: Sneha & Vikram each owe Rohan 300. Desserts: Sneha owes Vikram 300.
    assert detailed == {
        ("Sneha", "Rohan", 300, "Cab"),
        ("Vikram", "Rohan", 300, "Cab"),
        ("Sneha", "Vikram", 300, "Desserts"),
    }
    # Same balances, netted: Vikram owes Rohan 300 net (300 cab - ... ) — check net match.
    def net(txns):
        b = {p: 0 for p in r["people"]}
        for t in txns:
            b[t["from"]] -= t["amount"]
            b[t["to"]] += t["amount"]
        return b
    assert net(r["settlements"]) == net(r["settlementsDetailed"])
    # Simplified must use no more transactions than detailed.
    assert len(r["settlements"]) <= len(r["settlementsDetailed"])


def test_no_group_items_no_detailed():
    r = calculator.compute_split({
        "people": ["A", "B"],
        "items": [{"label": "X", "total": 100, "sharedBy": ["A", "B"],
                   "category": "other", "split": "equal", "payer": "self"}],
        "assumptions": [], "oneLiner": "",
    })
    assert r["settlements"] == [] and r["settlementsDetailed"] == []


def test_malformed_raises():
    for bad in [
        {},
        {"items": []},
        {"items": [{"label": "x", "total": "free", "sharedBy": ["A"]}]},
        {"items": [{"label": "x", "total": 10, "sharedBy": [], "split": "equal"}]},
    ]:
        try:
            calculator.compute_split(bad)
            assert False, f"expected ValueError for {bad}"
        except ValueError:
            pass


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)

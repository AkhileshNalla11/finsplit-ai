"""Deterministic split calculator.

Claude extracts the *structure* of a bill (people, items, who shared each item,
and how each item splits). This module does ALL the arithmetic, so the result
always balances by construction — it never depends on the model's math.

Input (Claude's extraction):
    {
      "people": ["A", "B"],
      "items": [
        # fixed-amount charge:
        {"label": str, "total": number, "sharedBy": [names],
         "category": "veg|nonveg|drinks|tax|other", "split": "equal|proportional",
         "payer": "<name>" | "self"},
        # percentage charge (e.g. 18% GST, 10% service, 15% tip):
        {"label": str, "rate": 0.18, "appliesTo": [labels of the items it's charged on],
         "category": "tax", "payer": "<name>" | "self"}
      ],
      "assumptions": [str],
      "oneLiner": str
    }

`payer` drives "who pays whom": a named person means they fronted the whole item
(group-funded); "self" (or missing) means each consumer paid their own portion, so
that item is already settled and excluded from the settlement. This lets a mixed
trip ("Kritik paid the hotel; everyone paid their own drinks") settle correctly —
only the group-funded items generate transactions.

Percentage items carry a `rate` (18% may be given as 0.18 or 18) and `appliesTo`
(labels of the base items). The calculator computes the amount = base × rate and
distributes it in proportion to each person's share of those base items — so GST on
the hotel is borne by whoever used the hotel, in proportion to their room cost.

`coveredBy` (optional, on any fixed item) is a {consumer: giver} map for GIFTS — a
giver absorbs the consumer's share as a treat. The consumer owes nothing for it and
NO repayment is created. This differs from `payer` (a loan that settles later): a
gift just reassigns who is responsible. E.g. coveredBy {"Priya": "Arjun"} on the
dinner makes Arjun bear Priya's share; Priya owes 0, no Priya->Arjun transaction.

Output adds the computed numeric fields the frontend renders
(`items[].perHead`, `perPerson`, `totalBill`) and keeps the same overall shape.
"""

from __future__ import annotations

import math

# Categories excluded from the "food base" that weights proportional (tax/
# service) charges — matching the rule "proportional to each person's food
# subtotal". Drinks and the tax itself don't count toward the base.
_FOOD_BASE_EXCLUDED = {"drinks", "tax"}


def _num(value, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number, got {value!r}")
    return float(value)


def _payer_of(item: dict) -> str | None:
    """The named payer of an item, or None for 'self'/unspecified (excluded from settlement)."""
    payer = item.get("payer")
    if isinstance(payer, str) and payer.strip() and payer.strip().lower() != "self":
        return payer.strip()
    return None


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_percentage(item: dict) -> bool:
    """A percentage charge has a positive `rate` and no fixed `total`."""
    rate = item.get("rate")
    return _is_number(rate) and rate > 0 and not _is_number(item.get("total"))


def _rate_fraction(item: dict) -> float:
    """Normalize a rate to a fraction: 18 -> 0.18, 0.18 -> 0.18."""
    rate = _num(item.get("rate"), f"item '{item.get('label', 'item')}'.rate")
    return rate / 100 if rate > 1 else rate


def _base_indices(item: dict, items: list[dict], is_pct: list[bool]) -> list[int]:
    """Indices of the FIXED items a percentage charge applies to (by label match)."""
    fixed = [i for i, pct in enumerate(is_pct) if not pct]
    raw = item.get("appliesTo")
    wanted = {str(x).strip().lower() for x in raw} if isinstance(raw, list) else set()
    if not wanted or wanted & {"all", "total", "everything"}:
        return fixed
    matched = [i for i in fixed if str(items[i].get("label", "")).strip().lower() in wanted]
    return matched or fixed  # if labels didn't match, fall back to the whole bill


def _covered_by(item: dict) -> dict[str, str]:
    """Map of {consumer: giver} for gifted shares — a giver absorbs the consumer's
    portion as a treat, so the consumer owes nothing and NO repayment is created
    (unlike `payer`, which is a loan settled later). Invalid/self entries dropped."""
    raw = item.get("coveredBy")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for consumer, giver in raw.items():
        if isinstance(consumer, str) and isinstance(giver, str) and giver.strip():
            giver = giver.strip()
            if consumer != giver:
                out[consumer] = giver
    return out


def _people_from(extraction: dict) -> list[str]:
    """Declared people, plus anyone referenced in an item's sharedBy, as a payer, or
    as a gift-giver (order-stable). Such people belong in the split even if they ate
    nothing themselves."""
    people: list[str] = [p for p in (extraction.get("people") or []) if isinstance(p, str)]
    seen = set(people)

    def add(name):
        if isinstance(name, str) and name not in seen:
            seen.add(name)
            people.append(name)

    for item in extraction["items"]:
        for name in item.get("sharedBy") or []:
            add(name)
        add(_payer_of(item))
        for giver in _covered_by(item).values():
            add(giver)
    if not people:
        raise ValueError("no people found in extraction")
    return people


def compute_split(extraction: dict) -> dict:
    """Turn Claude's structural extraction into a fully-computed, balanced split."""
    if not isinstance(extraction, dict):
        raise ValueError("extraction must be an object")
    items = extraction.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("extraction.items must be a non-empty list")

    people = _people_from(extraction)
    food_base: dict[str, float] = {p: 0.0 for p in people}
    # Per-item {person: share}, so settlement can attribute each item to its payer.
    allocs: list[dict[str, float]] = [{} for _ in items]
    # Each item's amount (given for fixed items, computed for percentage items).
    totals: list[float] = [0.0 for _ in items]
    is_pct = [_is_percentage(it) for it in items]

    # Pass 1 — fixed equal items: even share per person, and accumulate the food base.
    # A gifted share (coveredBy) is borne by the giver, not the consumer.
    for idx, item in enumerate(items):
        if is_pct[idx] or str(item.get("split") or "equal").lower() == "proportional":
            continue
        label = item.get("label", "item")
        total = _num(item.get("total"), f"item '{label}'.total")
        shared = [n for n in (item.get("sharedBy") or []) if isinstance(n, str)]
        category = str(item.get("category") or "other").lower()
        if not shared:
            raise ValueError(f"item '{label}' has no one in sharedBy")
        covers = _covered_by(item)
        totals[idx] = total
        share = total / len(shared)
        for p in shared:
            bearer = covers.get(p, p)  # giver bears a gifted share; else the consumer
            allocs[idx][bearer] = allocs[idx].get(bearer, 0.0) + share
            if category not in _FOOD_BASE_EXCLUDED:
                food_base[bearer] += share

    # Pass 2 — fixed proportional items: allocate weighted by food base (equal if none).
    for idx, item in enumerate(items):
        if is_pct[idx] or str(item.get("split") or "equal").lower() != "proportional":
            continue
        total = _num(item.get("total"), f"item '{item.get('label', 'item')}'.total")
        totals[idx] = total
        shared = [n for n in (item.get("sharedBy") or []) if isinstance(n, str)]
        covers = _covered_by(item)
        targets = shared or people
        base_sum = sum(food_base.get(p, 0.0) for p in targets)
        for p in targets:
            v = total * food_base.get(p, 0.0) / base_sum if base_sum > 0 else total / len(targets)
            bearer = covers.get(p, p)
            allocs[idx][bearer] = allocs[idx].get(bearer, 0.0) + v

    # Pass 3 — percentage items: amount = base × rate, borne in proportion to each
    # person's share of the base items (equal split if the base has no consumers).
    for idx, item in enumerate(items):
        if not is_pct[idx]:
            continue
        base_idxs = _base_indices(item, items, is_pct)
        amount = round(sum(totals[b] for b in base_idxs) * _rate_fraction(item))
        totals[idx] = amount
        weight: dict[str, float] = {}
        for b in base_idxs:
            for p, v in allocs[b].items():
                weight[p] = weight.get(p, 0.0) + v
        wsum = sum(weight.values())
        if wsum > 0:
            for p, w in weight.items():
                a = amount * w / wsum
                allocs[idx][p] = allocs[idx].get(p, 0.0) + a
        else:
            for p in people:
                a = amount / len(people)
                allocs[idx][p] = allocs[idx].get(p, 0.0) + a

    total_bill = round(sum(totals))
    # Reconcile EACH item's shares to integers summing to that item's total, then
    # derive perPerson from those same integers. Breakdown, perPerson, and settlements
    # are all built on one set of numbers, so they can never disagree by a rounding ₹1.
    int_allocs = [_reconcile(allocs[idx], round(totals[idx])) for idx in range(len(items))]
    per_person: dict[str, int] = {p: 0 for p in people}
    for ia in int_allocs:
        for p, amt in ia.items():
            per_person[p] = per_person.get(p, 0) + amt
    settlements, settlements_detailed, paid_by = _settle(items, int_allocs, totals, people)

    return {
        "people": people,
        "items": [_display_item(items[i], totals[i], int_allocs[i]) for i in range(len(items))],
        "perPerson": per_person,
        "totalBill": total_bill,
        "paidBy": paid_by,
        "settlements": settlements,
        "settlementsDetailed": settlements_detailed,
        "assumptions": list(extraction.get("assumptions") or []),
        "oneLiner": extraction.get("oneLiner", ""),
    }


def _display_item(item: dict, total: float, alloc: dict[str, float]) -> dict:
    """Item with its (computed) total and a display-only per-head.

    `sharedBy` lists everyone who *consumed* the item (the original sharers, or the
    bearers for percentage items). `gifted` flags consumers whose share was covered
    by someone else, so the UI can show e.g. "Priya (gifted)". per-head is over all
    consumers so it reflects the real per-person amount, not the post-gift bearers.
    """
    raw_shared = [n for n in (item.get("sharedBy") or []) if isinstance(n, str)]
    consumers = raw_shared or list(alloc.keys())
    covered = _covered_by(item)
    gifted = [c for c in consumers if c in covered]

    label = item.get("label", "item")
    if _is_percentage(item):
        label = f"{label} ({round(_rate_fraction(item) * 100)}%)"
    denom = len(consumers) if consumers else 1
    out = {
        "label": label,
        "total": round(total),
        "sharedBy": consumers,
        "category": str(item.get("category") or "other").lower(),
        "perHead": round(total / denom) if denom else 0,
    }
    if gifted:
        out["gifted"] = gifted
    return out


def _reconcile(exact: dict[str, float], target: int) -> dict[str, int]:
    """Round per-person amounts so they sum exactly to `target` (largest remainder)."""
    result = {p: math.floor(v) for p, v in exact.items()}
    remainder = target - sum(result.values())
    # Hand out (or claw back) the leftover rupees by largest fractional part.
    order = sorted(exact, key=lambda p: exact[p] - math.floor(exact[p]), reverse=True)
    n = len(order)
    if n and remainder > 0:
        for i in range(remainder):
            result[order[i % n]] += 1
    elif n and remainder < 0:
        for i in range(-remainder):
            result[order[-1 - (i % n)]] -= 1
    return result


def _settle(
    items: list[dict], int_allocs: list[dict[str, int]], totals: list[float], people: list[str]
) -> tuple[list[dict], list[dict], dict[str, int]]:
    """Settle only the GROUP-FUNDED items — those one named person fronted.

    Items paid "self" (or with no payer) are already settled and excluded, so a
    mixed trip settles its shared costs without being thrown off by self-paid ones.
    Uses the already-reconciled integer shares so it stays consistent with perPerson.

    Returns (simplified, detailed, paidBy):
      - detailed: every direct obligation — each bearer → the item's payer for their
        share of that item, tagged with the item label ("…for what").
      - simplified: the same balances netted to the fewest transactions.
    Both empty when nothing was group-funded.
    """
    group_paid: dict[str, int] = {p: 0 for p in people}
    net: dict[str, int] = {p: 0 for p in people}
    detailed: list[dict] = []
    group_total = 0

    for idx, item in enumerate(items):
        payer = _payer_of(item)
        if payer is None or payer not in group_paid:
            continue  # self-paid or unknown — not part of the settlement
        group_paid[payer] += round(totals[idx])
        group_total += round(totals[idx])
        # Each non-payer bearer owes the payer their share (the gross "who owes whom").
        for person, amt in int_allocs[idx].items():
            if person == payer or amt <= 0:
                continue
            detailed.append({"from": person, "to": payer, "amount": amt, "for": item.get("label", "item")})
            net[person] -= amt
            net[payer] += amt

    if group_total == 0:
        return [], [], {}

    paid_by = {p: amt for p, amt in group_paid.items() if amt}
    return _min_cash_flow(net), detailed, paid_by


def _min_cash_flow(net: dict[str, int]) -> list[dict]:
    """Greedy minimal 'who pays whom' from net balances (creditors > 0, debtors < 0)."""
    creditors = sorted(([p, v] for p, v in net.items() if v > 0), key=lambda x: -x[1])
    debtors = sorted(([p, -v] for p, v in net.items() if v < 0), key=lambda x: -x[1])

    settlements: list[dict] = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor, creditor = debtors[i], creditors[j]
        amount = min(debtor[1], creditor[1])
        if amount > 0:
            settlements.append({"from": debtor[0], "to": creditor[0], "amount": amount})
        debtor[1] -= amount
        creditor[1] -= amount
        if debtor[1] == 0:
            i += 1
        if creditor[1] == 0:
            j += 1
    return settlements

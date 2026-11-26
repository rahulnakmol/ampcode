#!/usr/bin/env python3
"""Calculate a supplied effort/cost range; never invent rates, fit, price or commitments."""

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_UP
import json
from pathlib import Path
import sys

from engagement import Invalid, digest, identifier, read_json


def number(value):
    if isinstance(value, bool):
        raise Invalid("Boolean is not an estimating quantity")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise Invalid("Invalid numeric input") from error
    if not result.is_finite() or result < 0:
        raise Invalid("Estimating numbers must be finite and nonnegative")
    return result


def calculate(packet):
    if not isinstance(packet, dict) or packet.get("schema") != 1:
        raise Invalid("Estimate schema 1 required")
    currency = packet.get("currency")
    if (not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha()
            or not currency.isupper() or not currency.isascii()):
        raise Invalid("Explicit three-letter currency required; no implicit currency conversion")
    date.fromisoformat(packet["rate_date"])
    for key in ("assumptions", "basis"):
        values = packet.get(key)
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
            raise Invalid(f"Nonempty {key} required")
    rows = packet.get("activities")
    if not isinstance(rows, list) or not rows:
        raise Invalid("Activities required")
    effort = [Decimal(0), Decimal(0)]
    cost = [Decimal(0), Decimal(0)]
    output, dependencies = [], {}
    for row in rows:
        key = identifier(row["id"])
        if key in dependencies:
            raise Invalid("Duplicate activity ID")
        if row.get("currency", currency) != currency:
            raise Invalid("Mixed currencies require an explicit reviewed conversion before estimating")
        if not all(isinstance(row.get(f), str) and row[f].strip() for f in ("activity", "role", "basis")):
            raise Invalid("Activity, role and estimating basis required per line")
        deps = row.get("after")
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps) or len(set(deps)) != len(deps):
            raise Invalid("Explicit unique predecessor IDs required")
        dependencies[key] = set(deps)
        quantity, rate = number(row["quantity"]), number(row["day_rate"])
        low, high = number(row["days_per_unit_low"]), number(row["days_per_unit_high"])
        if low > high or quantity == 0 or rate == 0 or high == 0:
            raise Invalid("Positive quantity/rate/upper effort and ordered effort bounds required")
        line_effort = [quantity * low, quantity * high]
        line_cost = [e * rate for e in line_effort]
        effort = [a + b for a, b in zip(effort, line_effort)]
        cost = [a + b for a, b in zip(cost, line_cost)]
        output.append({"id": key, "person_days": list(map(str, line_effort)), "base_cost": list(map(str, line_cost))})
    if any(dep not in dependencies for deps in dependencies.values() for dep in deps):
        raise Invalid("Unknown predecessor")
    remaining, stages = dict(dependencies), []
    while remaining:
        available = sorted(key for key, deps in remaining.items() if not deps)
        if not available:
            raise Invalid("Cyclic roadmap dependencies")
        stages.append(available)
        remaining = {key: deps - set(available) for key, deps in remaining.items() if key not in available}
    contingency = number(packet.get("contingency_percent"))
    if contingency > 100:
        raise Invalid("Contingency must be between 0 and 100 percent")
    reserve = [value * contingency / 100 for value in cost]
    return {"schema": 1, "input_hash": digest(packet), "currency": currency, "rate_date": packet["rate_date"],
            "activities": output, "person_days": list(map(str, effort)), "base_cost": list(map(str, cost)),
            "contingency_cost": list(map(str, reserve)), "total_cost": [str(a + b) for a, b in zip(cost, reserve)],
            "dependency_stages": stages, "assumptions": packet["assumptions"], "basis": packet["basis"],
            "limitations": "Arithmetic on supplied assumptions only. Person-days are not elapsed time; dependency stages are not a schedule. Cost is not price. Tax, expenses and commitments are not inferred."}


def office_values(model):
    """The bounded Office contract; leave the standalone calculator's range unchanged."""
    fields = {"schema", "currency", "rate_date", "assumptions", "basis", "contingency_percent", "activities"}
    if (not isinstance(model, dict) or set(model) != fields
            or type(model["schema"]) is not int or model["schema"] != 1
            or not isinstance(model["activities"], list) or not 1 <= len(model["activities"]) <= 1000):
        raise Invalid("Office estimates require a closed schema-1 model and 1–1000 activities")
    row_fields = {"id", "activity", "role", "basis", "quantity", "days_per_unit_low",
                  "days_per_unit_high", "day_rate", "after"}
    values = [model["contingency_percent"]]
    for row in model["activities"]:
        if not isinstance(row, dict) or set(row) not in (row_fields, row_fields | {"currency"}):
            raise Invalid("Unknown or missing Office estimate activity fields")
        values.extend(row[key] for key in ("quantity", "days_per_unit_low", "days_per_unit_high", "day_rate"))
    for value in values:
        parsed = number(value)
        digits = parsed.as_tuple()
        # Inspect the supplied representation without context rounding; normalize() could
        # erase a significant digit beyond the active Decimal precision.
        trailing = 0
        for digit in reversed(digits.digits):
            if digit:
                break
            trailing += 1
        if parsed > 1000000 or (parsed and digits.exponent + trailing < -6):
            raise Invalid("Office numeric inputs must be at most 1000000 with at most six decimal places")
    # Bounded inputs can yield up to 26 fractional digits after contingency. Preserve
    # them until the final rounding; default Decimal precision could lose a boundary digit.
    with localcontext() as context:
        context.prec = 60
        result = calculate(model)
        ranges = [result[key] for key in ("person_days", "base_cost", "contingency_cost", "total_cost")]
        ranges.extend(row[key] for row in result["activities"] for key in ("person_days", "base_cost"))
        if any(Decimal(value) > 1000000000 for values in ranges for value in values):
            raise Invalid("Office calculated magnitudes must not exceed 1000000000")
        result["display"] = {
            key: [format(Decimal(value).quantize(Decimal("0.000001" if key == "person_days" else "0.01"),
                                                rounding=ROUND_HALF_UP), "f") for value in result[key]]
            for key in ("person_days", "base_cost", "contingency_cost", "total_cost")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON assumptions and activity/rate inputs")
    args = parser.parse_args()
    try:
        print(json.dumps(calculate(read_json(Path(args.input))), indent=2))
    except (ValueError, TypeError, KeyError, OSError) as error:
        print(f"Estimate blocked: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

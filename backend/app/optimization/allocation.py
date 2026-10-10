"""Legacy CP-SAT draft allocation implementation."""

from collections import Counter

from fastapi import HTTPException
from ortools.sat.python import cp_model
from sqlalchemy import select

from ..models import AllocationPlan, Budget, Capacity, CareRequest, Facility, Service
from ..services.referrals import require


def optimize(session, day, limit):
    budget = require(session, Budget, 1)
    cap = min(limit, budget.total - budget.committed)
    demand = session.scalars(
        select(CareRequest)
        .where(CareRequest.day == day, CareRequest.status == "pending")
        .order_by(CareRequest.created_at)
    ).all()
    counts = Counter((request.zone, request.service_id) for request in demand)
    urgent = Counter((request.zone, request.service_id) for request in demand if request.priority == "urgent")
    candidates = []
    for (zone, service_id), count in sorted(counts.items()):
        offer = session.execute(
            select(Capacity, Facility)
            .join(Facility)
            .where(Facility.zone == zone, Capacity.service_id == service_id, Capacity.day == day)
            .order_by(Facility.id)
        ).first()
        if offer:
            capacity, facility = offer
            # Existing free slots cover demand before funding additional resources.
            available = (
                session.execute(
                    select(Capacity)
                    .join(Facility)
                    .where(Facility.zone == zone, Capacity.service_id == service_id, Capacity.day == day)
                )
                .scalars()
                .all()
            )
            unmet = max(
                0, count - sum(row.total - row.reserved - row.consumed for row in available)
            )
            if unmet:
                service = require(session, Service, service_id)
                candidates.append(
                    {
                        "facility_id": facility.id,
                        "facility_name": facility.name,
                        "service_id": service_id,
                        "service_name": service.name,
                        "zone": zone,
                        "unit_cost": service.unit_cost,
                        "max_units": unmet,
                        "urgent": min(unmet, urgent[(zone, service_id)]),
                    }
                )
    model = cp_model.CpModel()
    variables = [model.new_int_var(0, candidate["max_units"], f"units_{index}") for index, candidate in enumerate(candidates)]
    urgent_vars = [model.new_int_var(0, candidate["urgent"], f"urgent_{index}") for index, candidate in enumerate(candidates)]
    for units, priority in zip(variables, urgent_vars):
        model.add(priority <= units)
    cost = sum(variable * candidate["unit_cost"] for variable, candidate in zip(variables, candidates))
    model.add(cost <= cap)
    # Lexicographic objective: urgent demand, total served, then lower cost.
    max_demand = len(demand)
    multiplier = cap + 1
    model.maximize(sum(urgent_vars) * (max_demand + 1) * multiplier + sum(variables) * multiplier - cost)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    solver.parameters.num_search_workers = 1
    result = solver.solve(model)
    if result not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise HTTPException(422, "No feasible allocation could be found")
    allocations = [
        {key: value for key, value in candidate.items() if key not in ("max_units", "urgent")}
        | {"units": solver.value(variable)}
        for variable, candidate in zip(variables, candidates)
        if solver.value(variable) > 0
    ]
    plan = AllocationPlan(
        day=day,
        cost=sum(candidate["units"] * candidate["unit_cost"] for candidate in allocations),
        units=sum(candidate["units"] for candidate in allocations),
        allocations=allocations,
    )
    session.add(plan)
    session.flush()
    return plan

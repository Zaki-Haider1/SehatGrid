def item(version=1, **changes):
    return {
        "name": "Complete blood count",
        "category": "Laboratory",
        "price": 900,
        "daily_capacity": 30,
        "active": True,
        "version": version,
        **changes,
    }


def test_catalog_create_edit_delete_is_persisted_and_audited(pilot):
    p = pilot
    created = p.ok("facilities/P03/catalog", item(), "onboarder-p03")
    service = created["catalog"][0]
    assert created["version"] == 2
    assert service["price"] == 900
    assert p.ok("state", user="planner")["facilities"][2]["catalog"] == created["catalog"]
    edited = p.ok(
        f"facilities/P03/catalog/{service['id']}",
        item(2, price=1200, daily_capacity=25),
        "onboarder-p03",
        "PATCH",
    )
    assert edited["catalog"][0]["price"] == 1200
    assert edited["catalog"][0]["daily_capacity"] == 25
    deleted = p.ok(f"facilities/P03/catalog/{service['id']}", item(3), "onboarder-p03", "DELETE")
    assert deleted["catalog"] == []
    assert deleted["version"] == 4
    assert (
        len([a for a in p.ok("state", user="onboarder-p03")["audit"] if a["action"] == "CATALOG_UPDATED"])
        == 3
    )


def test_catalog_stale_or_invalid_write_has_no_effect(pilot):
    p = pilot
    p.ok("facilities/P03/catalog", item(), "onboarder-p03")
    before = p.ok("state", user="planner")
    assert p.call("facilities/P03/catalog", item(), "onboarder-p03").status_code == 409
    for changes in [{"price": -1}, {"daily_capacity": -1}, {"name": " "}, {"category": "Invalid"}]:
        assert p.call("facilities/P03/catalog", item(2, **changes), "onboarder-p03").status_code == 422
    after = p.ok("state", user="planner")
    assert after["facilities"] == before["facilities"]
    assert after["audit"] == before["audit"]


def test_onboarding_role_cannot_access_or_act_on_patient_requests(pilot):
    p = pilot
    view = p.ok("state", user="onboarder-p01")
    assert view["user"]["role"] == "onboarder"
    assert view["requests"] == view["referrals"] == view["plans"] == view["budgets"] == []
    assert p.call("requests/A-01/recommendations", user="onboarder-p01").status_code == 403
    assert (
        p.call(
            "requests/A-01/reprocess", {"reason": "Setup cannot reroute a patient"}, "onboarder-p01"
        ).status_code
        == 403
    )
    assert (
        p.call(
            "budgets", {"month": view["config"]["month"], "authorized": 50000, "version": 1}, "onboarder-p01"
        ).status_code
        == 403
    )


def test_catalog_permissions_are_facility_and_role_scoped(pilot):
    p = pilot
    for user in ["planner", "operator-p03", "onboarder-p02"]:
        assert p.call("facilities/P03/catalog", item(), user).status_code == 403
    assert p.ok("state", user="planner")["facilities"][2]["catalog"] == []


def test_onboarder_updates_owned_profile_service_and_capacity(pilot):
    p = pilot
    view = p.ok("state", user="onboarder-p03")
    f = view["facilities"][2]
    d = {k: f[k] for k in ["name", "ownership", "address", "zone", "latitude", "longitude", "version"]}
    d["name"] = "Demo updated campus P03"
    updated = p.ok("facilities/P03", d, "onboarder-p03", "PATCH")
    assert updated["name"] == d["name"]
    p.ok(
        "facilities/P03/services",
        {"eligible_zones": ["East"], "reviewed": True, "version": 2},
        "onboarder-p03",
    )
    day = view["config"]["service_date"]
    p.ok(
        f"facilities/P03/capacity/PRIMARY_CARE_OPD/{day}", {"quota": 12, "version": 1}, "onboarder-p03", "PUT"
    )
    assert p.ok("state", user="onboarder-p03")["facilities"][2]["capacities"][0]["quota"] == 12
    assert (
        p.call(
            f"facilities/P01/capacity/PRIMARY_CARE_OPD/{day}",
            {"quota": 12, "version": 1},
            "onboarder-p03",
            "PUT",
        ).status_code
        == 403
    )


def test_existing_demo_gains_onboarding_accounts_without_resetting_operations(pilot):
    from app.mvp.seed import seed

    p = pilot

    def legacy(s):
        for uid in list(s["users"]):
            if uid.startswith("onboarder-"):
                del s["users"][uid]
        for f in s["facilities"].values():
            del f["catalog"]

    p.edit(legacy)
    before = p.ok("state")
    with p.factory() as db:
        seed(db)
    after = p.ok("state")
    for key in ["requests", "referrals", "plans", "ledger", "budgets", "offers"]:
        assert after[key] == before[key]
    assert p.ok("auth/me", user="onboarder-p03")["role"] == "onboarder"
    assert all(f["catalog"] == [] for f in after["facilities"])

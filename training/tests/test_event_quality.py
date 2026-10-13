from training.event_quality import (
    candidate_storm_groups,
    exact_duplicate_groups,
    reported_event_time_semantics,
    stable_group_id,
)


def test_time_semantics_never_invents_local_24h_target():
    result = reported_event_time_semantics(1722297600000, "06:00")
    assert result["event_time_source_label"] == "06:00"
    assert result["event_time_label_is_approximate"] is True
    assert result["event_local_timezone"] == "unknown_or_unverified"
    assert result["event_local_instant_verified"] is False
    assert result["usable_for_24h_forecast_target"] is False
    unknown = reported_event_time_semantics(None, "unknown")
    assert unknown["source_event_date_rendered_utc"] is None
    assert unknown["event_time_source_label"] == "unknown"
    assert unknown["event_time_label_is_approximate"] is False


def test_exact_duplicates_are_separate_from_near_storm_candidates():
    rows = [
        {
            "event_id": 1,
            "reported_utc_calendar_date": "2024-07-30",
            "latitude": 11.5,
            "longitude": 76.1,
        },
        {
            "event_id": 1,
            "reported_utc_calendar_date": "2024-07-30",
            "latitude": 11.6,
            "longitude": 76.1,
        },
        {
            "event_id": 2,
            "reported_utc_calendar_date": "2024-07-31",
            "latitude": 11.51,
            "longitude": 76.1,
        },
    ]
    assert exact_duplicate_groups(rows) == [[0, 1]]
    # Distinct IDs remain visible but can be joined for split-leakage sensitivity.
    nearby = [
        {
            "event_id": 2,
            "reported_utc_calendar_date": "2024-07-31",
            "latitude": 11.51,
            "longitude": 76.1,
        },
        {
            "event_id": 3,
            "reported_utc_calendar_date": "2024-08-01",
            "latitude": 11.52,
            "longitude": 76.1,
        },
    ]
    groups = candidate_storm_groups(nearby, radius_km=5, max_day_gap=2)
    assert groups == [[0, 1]]
    assert stable_group_id(nearby, groups[0]) == stable_group_id(nearby, [1, 0])


def test_storm_candidates_require_explicit_parameters_and_are_transitive():
    rows = [
        {
            "event_id": 1,
            "reported_utc_calendar_date": "2024-07-30",
            "latitude": 11.50,
            "longitude": 76.10,
        },
        {
            "event_id": 2,
            "reported_utc_calendar_date": "2024-07-31",
            "latitude": 11.53,
            "longitude": 76.10,
        },
        {
            "event_id": 3,
            "reported_utc_calendar_date": "2024-08-01",
            "latitude": 11.56,
            "longitude": 76.10,
        },
        {
            "event_id": 4,
            "reported_utc_calendar_date": "2024-08-01",
            "latitude": 12.5,
            "longitude": 76.1,
        },
    ]
    assert candidate_storm_groups(rows, radius_km=5, max_day_gap=1) == [[0, 1, 2]]
    assert candidate_storm_groups(rows, radius_km=2, max_day_gap=1) == []


def test_catalog_binary_zero_is_explicitly_not_verified_safe_or_negative():
    from training.event_quality import catalog_label_semantics

    semantics = catalog_label_semantics(0)
    assert semantics["case_status"] == "sampled_no_nearby_catalog_report"
    assert semantics["negative_is_verified_non_event"] is False
    assert semantics["negative_is_verified_safe"] is False
    assert semantics["target_is_real_world_failure_probability"] is False
    assert catalog_label_semantics(1)["case_status"] == "catalog_reported_event"

import pandas as pd
import pytest

from ui.library_engine import (
    LibraryValidationResult,
    apply_library_mutations,
    compute_id_diff,
    rows_to_df,
)


def test_rows_to_df_returns_empty_frame_with_columns():
    df = rows_to_df([], ["id", "brand", "model"])
    assert list(df.columns) == ["id", "brand", "model"]
    assert df.empty


def test_compute_id_diff_detects_deleted_and_remaining_ids():
    original = pd.DataFrame([{"id": 1}, {"id": 2}, {"id": 3}])
    edited = pd.DataFrame([{"id": 2}, {"id": 3}, {"id": 4}])

    original_ids, edited_ids = compute_id_diff(original, edited, "id")
    assert original_ids == {1, 2, 3}
    assert edited_ids == {2, 3, 4}


def test_apply_library_mutations_routes_delete_create_update(monkeypatch):
    original_df = pd.DataFrame(
        [
            {"id": 1, "brand": "A", "model": "M1", "code": "", "opening_angle_deg": 110},
            {"id": 2, "brand": "B", "model": "M2", "code": "", "opening_angle_deg": 120},
        ]
    )
    edited_df = pd.DataFrame(
        [
            {"id": 2, "brand": "B2", "model": "M2", "code": "X", "opening_angle_deg": 120},
            {"id": None, "brand": "C", "model": "M3", "code": "Y", "opening_angle_deg": 100},
        ]
    )

    deletes, creates, updates = [], [], []

    def validate_row(row):
        return LibraryValidationResult(True)

    def build_payload(row):
        return {
            "brand": row["brand"],
            "model": row["model"],
            "code": row["code"],
            "opening_angle_deg": int(row["opening_angle_deg"]),
        }

    apply_library_mutations(
        original_df=original_df,
        edited_df=edited_df,
        id_column="id",
        validate_row=validate_row,
        build_create_payload=build_payload,
        build_update_payload=build_payload,
        create_row=lambda **kwargs: creates.append(kwargs),
        update_row=lambda row_id, **kwargs: updates.append((row_id, kwargs)),
        delete_row=lambda row_id: deletes.append(row_id),
    )

    assert deletes == [1]
    assert updates == [(2, {"brand": "B2", "model": "M2", "code": "X", "opening_angle_deg": 120})]
    assert creates == [{"brand": "C", "model": "M3", "code": "Y", "opening_angle_deg": 100}]


def test_apply_library_mutations_stops_on_validation_error(monkeypatch):
    class StopCalled(Exception):
        pass

    import ui.library_engine as engine

    errors = []
    monkeypatch.setattr(engine.st, "error", lambda msg: errors.append(msg))
    monkeypatch.setattr(engine.st, "stop", lambda: (_ for _ in ()).throw(StopCalled()))

    original_df = pd.DataFrame([{"id": 1, "brand": "A", "model": "M1", "code": "", "opening_angle_deg": 110}])
    edited_df = pd.DataFrame([{"id": 1, "brand": "", "model": "M1", "code": "", "opening_angle_deg": 110}])

    with pytest.raises(StopCalled):
        apply_library_mutations(
            original_df=original_df,
            edited_df=edited_df,
            id_column="id",
            validate_row=lambda _: LibraryValidationResult(False, "Each row must have Brand and Model."),
            build_create_payload=lambda row: row,
            build_update_payload=lambda row: row,
            create_row=lambda **kwargs: None,
            update_row=lambda row_id, **kwargs: None,
            delete_row=lambda row_id: None,
        )

    assert errors == ["Each row must have Brand and Model."]

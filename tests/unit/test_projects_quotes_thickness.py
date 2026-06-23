import pytest

from corequote_api.projects_quotes_errors import WorkspaceValidationError
from corequote_api.projects_quotes_payloads import _clean_unit_payload
from corequote_api.projects_quotes_pricing import _to_runtime_unit
from corequote_api.schemas import CutlistUnitRequest
from corequote_api.services import preview_cutlist


class FakeRuntimeService:
    def __init__(self):
        self.calls: list[dict] = []

    def build_preview(self, *, company_id: str, units: list[dict], use_db_rulesets: bool) -> dict:
        self.calls.append(
            {
                "company_id": company_id,
                "units": units,
                "use_db_rulesets": use_db_rulesets,
            }
        )
        return {
            "carcass": [],
            "panels": [],
            "hardware": [],
            "extras": [],
            "runtime_rows": [],
            "runtime_mode": "legacy",
            "unit_sources": [],
        }


def test_clean_unit_payload_does_not_accept_client_thickness_as_store_data():
    payload = _clean_unit_payload(
        {
            "unit_type_key": "Base Door",
            "height": 780,
            "width": 600,
            "depth": 580,
            "thickness": 99,
            "carcass_board_type_id": "board-1",
            "door_board_type_id": "board-2",
        }
    )

    assert "thickness" not in payload


def test_runtime_unit_uses_unit_carcass_board_thickness():
    unit = {
        "unit_number": 1,
        "unit_type_key": "Base Door",
        "height": 780,
        "width": 600,
        "depth": 580,
        "thickness": 16,
        "carcass_board_type_id": "board-18",
        "extra_params": {},
    }

    result = _to_runtime_unit(
        unit,
        quote={"default_carcass_board_type_id": "board-16"},
        board_lookup={"board-16": {"thickness": 16}, "board-18": {"thickness": 18}},
        default_slide=None,
    )

    assert result["thickness"] == 18


def test_runtime_unit_uses_quote_default_carcass_board_thickness():
    unit = {
        "unit_number": 1,
        "unit_type_key": "Base Door",
        "height": 780,
        "width": 600,
        "depth": 580,
        "thickness": 16,
        "carcass_board_type_id": None,
        "extra_params": {},
    }

    result = _to_runtime_unit(
        unit,
        quote={"default_carcass_board_type_id": "board-19"},
        board_lookup={"board-19": {"thickness": 19}},
        default_slide=None,
    )

    assert result["thickness"] == 19


def test_runtime_unit_requires_effective_carcass_board():
    unit = {
        "unit_number": 1,
        "unit_type_key": "Base Door",
        "height": 780,
        "width": 600,
        "depth": 580,
        "thickness": 16,
        "carcass_board_type_id": None,
        "extra_params": {},
    }

    with pytest.raises(WorkspaceValidationError, match="carcass board is required"):
        _to_runtime_unit(
            unit,
            quote={"default_carcass_board_type_id": None},
            board_lookup={},
            default_slide=None,
        )


def test_preview_cutlist_resolves_thickness_from_request_board_type():
    runtime_service = FakeRuntimeService()
    unit = CutlistUnitRequest.model_validate(
        {
            "unit_number": 1,
            "unit_type": "Base Door",
            "height": 780,
            "width": 600,
            "depth": 580,
            "board_type_id": "board-18",
            "extra_params": {"num_doors": 2},
        }
    )

    preview_cutlist(
        [unit],
        company_id="company-1",
        runtime_service=runtime_service,
        use_db_rulesets=False,
        board_thickness_lookup=lambda _company_id, _board_ids: {"board-18": 18},
    )

    assert runtime_service.calls[0]["units"][0]["thickness"] == 18
    assert "board_type_id" not in runtime_service.calls[0]["units"][0]


def test_preview_cutlist_attaches_selected_profile_handle_lookup():
    runtime_service = FakeRuntimeService()
    unit = CutlistUnitRequest.model_validate(
        {
            "unit_number": 1,
            "unit_type": "Base Door",
            "height": 780,
            "width": 900,
            "depth": 580,
            "board_type_id": "board-18",
            "extra_params": {
                "num_doors": 2,
                "base_door_top_j_channel_handle_id": "handle-j",
            },
        }
    )

    preview_cutlist(
        [unit],
        company_id="company-1",
        runtime_service=runtime_service,
        use_db_rulesets=False,
        board_thickness_lookup=lambda _company_id, _board_ids: {"board-18": 18},
        handle_lookup=lambda _company_id, _handle_ids: {
            "handle-j": {
                "id": "handle-j",
                "name": "J Rail",
                "handle_type": "j_channel",
                "front_reduction_mm": 24,
            }
        },
    )

    extra_params = runtime_service.calls[0]["units"][0]["extra_params"]
    assert extra_params["_profile_handle_lookup"]["handle-j"]["handle_type"] == "j_channel"

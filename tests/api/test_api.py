from fastapi.testclient import TestClient

from corequote_api.main import app


client = TestClient(app)


def test_health_endpoints():
    assert client.get("/health/live").json() == {"status": "ok", "service": "corequote-api"}
    assert client.get("/health/ready").json() == {"status": "ok", "service": "corequote-api"}


def test_cutlist_preview_uses_core_cutlist_logic():
    response = client.post(
        "/api/v1/cutlists/preview",
        json={
            "units": [
                {
                    "unit_number": 1,
                    "unit_type": "Base Door",
                    "height": 780,
                    "width": 900,
                    "depth": 560,
                    "thickness": 16,
                    "extra_params": {"num_doors": 2, "num_shelves": 1},
                }
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert {"unit_number": 1, "desc": "Side", "length": 748, "width": 544, "qty": 2} in body["carcass"]
    assert {"unit_number": 1, "desc": "Door", "length": 777, "width": 447, "qty": 2} in body["panels"]


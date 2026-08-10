"""Unit tests verifying the backend transcription and translation endpoint.

Tests mock UploadFile submissions and verify translation routing outputs.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user
from unittest.mock import MagicMock

client = TestClient(app)


@pytest.mark.asyncio
async def test_transcription_endpoint_regional_fallbacks() -> None:
    """
    Verifies that calling POST /api/v1/transcribe translates regional languages
    correctly using the Whisper mock fallback.
    """
    # Mock authentication dependency
    mock_user = MagicMock()
    mock_user.id = "00000000-0000-0000-0000-000000000000"
    mock_user.email = "test@buildsense.com"

    # Use FastAPI dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        # 1. Test Malayalam Translation (Logistics triggers)
        res_malayalam = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.webm", b"mock-audio-bytes-malayalam", "audio/webm")},
            data={"language": "Malayalam"}
        )
        assert res_malayalam.status_code == 200
        assert "trucks" in res_malayalam.json()["transcript"]
        assert "Google Maps" in res_malayalam.json()["transcript"]

        # 2. Test Hindi Translation (Wholesale triggers)
        res_hindi = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.webm", b"mock-audio-bytes-hindi", "audio/webm")},
            data={"language": "Hindi"}
        )
        assert res_hindi.status_code == 200
        assert "wholesale" in res_hindi.json()["transcript"]
        assert "distribution" in res_hindi.json()["transcript"]

        # 3. Test Tamil Translation (Manufacturing triggers)
        res_tamil = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.webm", b"mock-audio-bytes-tamil", "audio/webm")},
            data={"language": "Tamil"}
        )
        assert res_tamil.status_code == 200
        assert "manufacturing" in res_tamil.json()["transcript"] or "batch" in res_tamil.json()["transcript"]
        assert "reactive" in res_tamil.json()["transcript"]
    finally:
        app.dependency_overrides.clear()

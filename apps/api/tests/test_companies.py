"""Unit tests verifying the company baseline creation, listing, and project mapping.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user
from app.db.postgres import postgres_client
from unittest.mock import MagicMock

client = TestClient(app)


@pytest.mark.asyncio
async def test_postgres_client_companies_mock_crud() -> None:
    """
    Verifies companies CRUD in mock database client mode.
    """
    user_id = "00000000-0000-0000-0000-000000000000"
    
    # Ensure client is mock mode
    postgres_client.is_mock = True
    
    company_id = await postgres_client.create_company(
        user_id=user_id,
        name="Mock Logistics Corp",
        industry="Logistics & Fleet",
        core_tools="Excel, Telematics"
    )
    
    assert company_id is not None
    
    # Retrieve company
    company = await postgres_client.get_company(company_id)
    assert company is not None
    assert company["name"] == "Mock Logistics Corp"
    assert company["industry"] == "Logistics & Fleet"
    assert company["core_tools"] == "Excel, Telematics"
    
    # Get user companies
    companies = await postgres_client.get_user_companies(user_id)
    assert len(companies) > 0
    assert any(c["id"] == company_id for c in companies)


@pytest.mark.asyncio
async def test_companies_endpoints_and_mapping() -> None:
    """
    Verifies HTTP endpoints for companies and maps to projects.
    """
    mock_user = MagicMock()
    mock_user.id = "00000000-0000-0000-0000-000000000000"
    mock_user.email = "test@buildsense.com"

    app.dependency_overrides[get_current_user] = lambda: mock_user
    postgres_client.is_mock = True
    
    try:
        # 1. Create company
        res_create = client.post(
            "/api/v1/companies",
            json={
                "name": "Acme Manufacturing",
                "industry": "Manufacturing",
                "core_tools": "SAP, QuickBooks"
            }
        )
        assert res_create.status_code == 200
        company_id = res_create.json()["company_id"]
        assert company_id is not None

        # 2. List companies
        res_list = client.get("/api/v1/companies")
        assert res_list.status_code == 200
        companies = res_list.json()
        assert len(companies) > 0
        assert any(c["id"] == company_id for c in companies)

        # 3. Create project mapped to company
        res_proj = client.post(
            "/api/v1/projects",
            json={
                "title": "Machine Line Optimization",
                "description": "Reduce machine downtime bottleneck",
                "mode": "OPTIMIZER",
                "motivation": "REVENUE",
                "user_persona": "Solo Founder",
                "company_id": company_id
            }
        )
        assert res_proj.status_code == 200
        project_id = res_proj.json()["project_id"]
        assert project_id is not None

        # 4. Fetch project details and check company_id
        res_get_proj = client.get(f"/api/v1/projects/{project_id}")
        assert res_get_proj.status_code == 200
        proj_data = res_get_proj.json()
        assert proj_data["company_id"] == company_id

    finally:
        app.dependency_overrides.clear()

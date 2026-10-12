"""Tests for LazyVoltApiClient."""
from __future__ import annotations

from collections.abc import AsyncIterator

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.lazyvolt.api import (
    LazyVoltApiClient,
    LazyVoltApiError,
    LazyVoltAuthError,
)


CLOUD_URL = "http://localhost:80"


@pytest.fixture
async def session(hass, aioclient_mock: AiohttpClientMocker) -> AsyncIterator[aiohttp.ClientSession]:
    session = aioclient_mock.create_session(hass.loop)
    yield session
    await session.close()


@pytest.fixture
def client(session) -> LazyVoltApiClient:
    return LazyVoltApiClient(CLOUD_URL, session)


@pytest.fixture
def authed_client(session) -> LazyVoltApiClient:
    return LazyVoltApiClient(CLOUD_URL, session, token="1|abc")


async def test_authenticate_returns_token(client, aioclient_mock):
    aioclient_mock.post(f"{CLOUD_URL}/api/v1/edge/auth", json={"token": "1|newtoken"})

    token = await client.authenticate("user@example.com", "secret", "Home Assistant")

    assert token == "1|newtoken"
    assert aioclient_mock.mock_calls[0][2]["edge_name"] == "Home Assistant"


async def test_authenticate_raises_auth_error_on_422(client, aioclient_mock):
    aioclient_mock.post(f"{CLOUD_URL}/api/v1/edge/auth", status=422)

    with pytest.raises(LazyVoltAuthError):
        await client.authenticate("bad@user.com", "wrong", "HA")


async def test_authenticate_raises_api_error_on_connection_failure(client, aioclient_mock):
    aioclient_mock.post(f"{CLOUD_URL}/api/v1/edge/auth", exc=aiohttp.ClientConnectionError())

    with pytest.raises(LazyVoltApiError):
        await client.authenticate("user@example.com", "secret", "HA")


async def test_get_decision_returns_mode(authed_client, aioclient_mock):
    aioclient_mock.get(
        f"{CLOUD_URL}/api/v1/edge/decision",
        json={"mode": "SOLAR", "phases": 1, "amps": 6},
    )

    decision = await authed_client.get_decision()

    assert decision["mode"] == "SOLAR"
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == "Bearer 1|abc"


async def test_get_decision_raises_on_error(authed_client, aioclient_mock):
    aioclient_mock.get(f"{CLOUD_URL}/api/v1/edge/decision", status=500)

    with pytest.raises(LazyVoltApiError):
        await authed_client.get_decision()


async def test_get_decision_raises_auth_error_when_token_revoked(authed_client, aioclient_mock):
    """A revoked edge token (401) is an auth error, not a transient outage."""
    aioclient_mock.get(f"{CLOUD_URL}/api/v1/edge/decision", status=401)

    with pytest.raises(LazyVoltAuthError):
        await authed_client.get_decision()


async def test_get_decision_timeout_is_api_error(authed_client, aioclient_mock):
    """A Cloud timeout is reported like any other outage, not as an unhandled error."""
    aioclient_mock.get(f"{CLOUD_URL}/api/v1/edge/decision", exc=TimeoutError())

    with pytest.raises(LazyVoltApiError):
        await authed_client.get_decision()


async def test_post_telemetry_sends_payload(authed_client, aioclient_mock):
    aioclient_mock.post(f"{CLOUD_URL}/api/v1/edge/telemetry", status=204)

    await authed_client.post_telemetry({"mode": "SOLAR", "charger_status": "charging"})

    assert aioclient_mock.mock_calls[0][2] == {"mode": "SOLAR", "charger_status": "charging"}


async def test_post_progress_ignores_404_no_active_goal(authed_client, aioclient_mock):
    aioclient_mock.post(f"{CLOUD_URL}/api/v1/edge/progress", status=404)

    await authed_client.post_progress(1_000_000)

    assert aioclient_mock.call_count == 1


async def test_post_progress_sends_wh(authed_client, aioclient_mock):
    aioclient_mock.post(f"{CLOUD_URL}/api/v1/edge/progress", json={"kwh_charged": 5.0})

    await authed_client.post_progress(5_000_000)

    assert aioclient_mock.mock_calls[0][2] == {"meter_energy_total_wh": 5_000_000}

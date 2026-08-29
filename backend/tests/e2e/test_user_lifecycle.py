"""End-to-end: the life of an account, through the API and the WhatsApp it sends.

Nothing here reaches into the services or the models. Every step is an HTTP
call, in the order a real person would make them: the owner creates the access,
its holder is invited, sets their own password, works, changes it, and is
eventually deactivated and brought back.

The one thing that is not an HTTP call is reading the message the platform
sent, and that is deliberate: the invitation link never travels through the
API — it goes to a phone, and the API would be leaking a credential if it
returned it. So the test reads it where the person reads it, out of the
message that was queued.
"""

import re
from collections.abc import Iterator
from typing import Any

import pytest
from httpx import AsyncClient

from app.modules.identity.models import User, UserRole
from app.modules.notifications import tasks as notification_tasks
from tests.conftest import API_PREFIX
from tests.factories.user_factory import DEFAULT_PASSWORD

CHOSEN_PASSWORD = "clave-elegida-2026"
NEW_PASSWORD = "otra-clave-2026"


def bearer(token: str) -> dict[str, str]:
    """The header a client sends once it holds a session."""
    return {"Authorization": f"Bearer {token}"}


class Messages:
    """What the platform sent to a phone, instead of sending it."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def delay(self, phone: str, message: str, *args: Any, **kwargs: Any) -> None:
        self.sent.append((phone, message))

    def link_for(self, phone: str) -> str:
        """The token out of the last link sent to that number."""
        for number, message in reversed(self.sent):
            if number == phone:
                found = re.search(r"/(?:invitacion|recuperar)/([\w-]+)", message)
                assert found, f"no link in the message sent to {phone}: {message!r}"
                return found.group(1)
        raise AssertionError(f"nothing was sent to {phone}")


@pytest.fixture
def messages(monkeypatch: pytest.MonkeyPatch) -> Iterator[Messages]:
    """The WhatsApp messages, captured rather than queued."""
    recorder = Messages()
    monkeypatch.setattr(notification_tasks, "send_access_link", recorder)
    yield recorder


@pytest.mark.e2e
@pytest.mark.database
class TestUserLifecycle:
    """From "give Ana an account" to "Ana no longer works here"."""

    async def test_the_full_life_of_an_account(
        self, owner_client: AsyncClient, client: AsyncClient, messages: Messages
    ) -> None:
        """Invite, set a password, work, change it, deactivate, come back."""
        phone = "+5491166667777"

        # --- The owner hands out the access, not a password ---------------
        created = await owner_client.post(
            f"{API_PREFIX}/users",
            json={
                "email": "ana@example.com",
                "name": "Ana",
                "last_name": "Gómez",
                "phone": phone,
                "role": UserRole.PURCHASING.value,
            },
        )
        assert created.status_code == 201
        user_id = created.json()["id"]
        # Nothing that could let anybody in comes back in the response.
        assert "token" not in created.text and "password" not in created.text

        # --- Until she redeems it, the access does not work ----------------
        assert (
            await client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": "ana@example.com", "password": CHOSEN_PASSWORD},
            )
        ).status_code == 401

        # --- She gets the invitation on her phone and sets her password ----
        invitation = messages.link_for(phone)
        assert (await client.get(f"{API_PREFIX}/auth/invitation/{invitation}")).json() == {
            "usable": True
        }

        accepted = await client.post(
            f"{API_PREFIX}/auth/invitation/{invitation}",
            json={"new_password": CHOSEN_PASSWORD},
        )
        assert accepted.status_code == 204

        # The link works once.
        assert (
            await client.post(
                f"{API_PREFIX}/auth/invitation/{invitation}",
                json={"new_password": "todavia-otra-2026"},
            )
        ).status_code == 422

        # --- Ana logs in with the password only she knows ------------------
        logged_in = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": "ana@example.com", "password": CHOSEN_PASSWORD},
        )
        assert logged_in.status_code == 200
        token = logged_in.json()["access_token"]
        assert logged_in.json()["user"]["role"] == UserRole.PURCHASING.value

        # --- She reads who she is, and what she may reach ------------------
        me = await client.get(f"{API_PREFIX}/auth/me", headers=bearer(token))
        assert me.status_code == 200
        assert me.json()["user"]["id"] == user_id
        # The menu is drawn from this, so it has to say both things.
        assert me.json()["permissions"]["SUPPLIERS"] == 2
        assert me.json()["permissions"]["SALES"] == 0

        # --- She does the work her role allows -----------------------------
        assert (
            await client.get(f"{API_PREFIX}/operations/jobs", headers=bearer(token))
        ).status_code == 200

        # --- But not the owner's -------------------------------------------
        assert (
            await client.get(f"{API_PREFIX}/operations/parameters", headers=bearer(token))
        ).status_code == 403

        # --- She changes her password --------------------------------------
        changed = await client.post(
            f"{API_PREFIX}/auth/password/change",
            headers=bearer(token),
            json={"current_password": CHOSEN_PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert changed.status_code == 204

        with_old = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": "ana@example.com", "password": CHOSEN_PASSWORD},
        )
        assert with_old.status_code == 401

        with_new = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": "ana@example.com", "password": NEW_PASSWORD},
        )
        assert with_new.status_code == 200
        new_token = with_new.json()["access_token"]

        # --- She leaves the team -------------------------------------------
        deactivated = await owner_client.post(f"{API_PREFIX}/users/{user_id}/deactivate")
        assert deactivated.status_code == 204

        # The session she was holding is closed on the spot...
        assert (
            await client.get(f"{API_PREFIX}/auth/me", headers=bearer(new_token))
        ).status_code == 401

        # ...and she cannot open a new one.
        assert (
            await client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": "ana@example.com", "password": NEW_PASSWORD},
            )
        ).status_code == 401

        # The account is still there, so what she did keeps her name.
        listed = await owner_client.get(f"{API_PREFIX}/users/{user_id}")
        assert listed.status_code == 200
        assert listed.json()["is_active"] is False
        assert listed.json()["name"] == "Ana"

        # --- And she comes back, as the same person -------------------------
        back = await owner_client.post(f"{API_PREFIX}/users/{user_id}/reactivate")
        assert back.status_code == 200
        assert back.json()["id"] == user_id

        # The password she used before does not come back with her.
        assert (
            await client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": "ana@example.com", "password": NEW_PASSWORD},
            )
        ).status_code == 401

        # She is invited again, and chooses another one.
        second_invitation = messages.link_for(phone)
        assert second_invitation != invitation
        assert (
            await client.post(
                f"{API_PREFIX}/auth/invitation/{second_invitation}",
                json={"new_password": "la-de-la-vuelta-2026"},
            )
        ).status_code == 204
        assert (
            await client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": "ana@example.com", "password": "la-de-la-vuelta-2026"},
            )
        ).status_code == 200

    async def test_the_owner_configures_the_platform(
        self, owner_client: AsyncClient, purchasing_client: AsyncClient
    ) -> None:
        """A business rule changes without a deploy, and only the owner may change it."""
        # --- The owner writes the parameters ------------------------------
        written = await owner_client.put(
            f"{API_PREFIX}/operations/parameters",
            json={
                "items": [
                    {
                        "key": "extraction.hour",
                        "value": 3,
                        "description": "Hora de la extracción nocturna",
                    },
                    {"key": "matching.threshold", "value": 0.87},
                ]
            },
        )
        assert written.status_code == 200
        assert len(written.json()) == 2

        # --- And reads them back ------------------------------------------
        stored = await owner_client.get(f"{API_PREFIX}/operations/parameters")
        assert stored.status_code == 200
        values = {item["key"]: item["value"] for item in stored.json()}
        assert values == {"extraction.hour": 3, "matching.threshold": 0.87}

        # --- Purchasing cannot see or change them --------------------------
        assert (
            await purchasing_client.get(f"{API_PREFIX}/operations/parameters")
        ).status_code == 403

    async def test_a_forgotten_password_is_recovered_without_leaking_the_account(
        self, client: AsyncClient, sales_user: User, messages: Messages
    ) -> None:
        """The recovery form answers the same whether or not the address exists,
        and the link that does exist goes out to a phone and not to the caller.
        """
        # Act
        known = await client.post(
            f"{API_PREFIX}/auth/password-reset/request", json={"email": sales_user.email}
        )
        unknown = await client.post(
            f"{API_PREFIX}/auth/password-reset/request",
            json={"email": "no-existe@example.com"},
        )

        # Assert
        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()
        # The token is a credential: it is never in the response.
        assert "token" not in known.text

        # The account still works with its original password.
        assert (
            await client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": sales_user.email, "password": DEFAULT_PASSWORD},
            )
        ).status_code == 200

        # One message went out, to the one address that exists, and it carries
        # a link that works.
        assert len(messages.sent) == 1
        recovery = messages.link_for(sales_user.phone)
        assert (
            await client.post(
                f"{API_PREFIX}/auth/password-reset/{recovery}",
                json={"new_password": NEW_PASSWORD},
            )
        ).status_code == 204

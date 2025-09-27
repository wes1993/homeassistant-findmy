"""The FindMy hub."""

from dataclasses import dataclass
from typing import Any
from datetime import datetime

from findmy.accessory import FindMyAccessory
from findmy.reports import AsyncAppleAccount, RemoteAnisetteProvider, LocalAnisetteProvider
from findmy.reports.state import LoginState
from findmy.reports.twofactor import AsyncSmsSecondFactor


@dataclass(frozen=True)
class FindMyReport:
    """Find My report."""

    latitude: float
    longitude: float
    accuracy: float
    timestamp: datetime


class FindMyHub:
    """Hub for Find My integration."""

    accessory: FindMyAccessory | None = None

    def __init__(self, url: str | None = None) -> None:
        """Initialize hub.

        Args:
            url: se None → usa anisette **locale**,
                 se stringa → anisette remoto con quell’URL.
        """
        if url is None or url.strip() == "" or url == "http://localhost:6969":
            # Locale (server anisette su localhost:6969)
            self.anisette = LocalAnisetteProvider(libs_path="ani_libs.bin")
        else:
            # Remoto (server anisette personalizzato)
            self.anisette = RemoteAnisetteProvider(url)

        self.account = AsyncAppleAccount(anisette=self.anisette)
        self.methods: list[AsyncSmsSecondFactor] = []

    async def authenticate(self, email: str, password: str) -> LoginState:
        """Authenticate with Apple ID credentials."""
        return await self.account.login(email, password)

    def restore_account(self, account: dict[str, Any]) -> None:
        """Restore account from saved JSON."""
        self.account.from_json(account)

    async def get_2fa_methods(self) -> list[tuple[str, str]]:
        """Get available two-factor methods (only SMS supported)."""
        self.methods = await self.account.get_2fa_methods()
        self.methods = [m for m in self.methods if isinstance(m, AsyncSmsSecondFactor)]

        return [
            (str(i), f"SMS {method.phone_number}")
            for i, method in enumerate(self.methods)
        ]

    async def request_two_factor(self, method_index: int) -> None:
        """Trigger 2FA code delivery (SMS)."""
        method = self.methods[method_index]
        return await method.request()

    async def submit_two_factor(self, method_index: int, code: str) -> LoginState:
        """Submit 2FA code."""
        method = self.methods[method_index]
        return await method.submit(code)

    def get_account_credentials(self) -> dict[str, Any]:
        """Export account credentials as JSON."""
        return self.account.to_json()

    def load_plist(self, plist: str) -> None:
        """Load accessory from base64/text plist."""
        self.accessory = FindMyAccessory.from_plist(bytes(plist, "utf-8"))

    async def get_position(self) -> FindMyReport:
        """Get the latest position report."""
        if self.accessory is None:
            raise ValueError("Accessory not loaded")

        reports = await self.account.fetch_last_reports(self.accessory)
        latest_report = sorted(reports, reverse=True)[0]

        return FindMyReport(
            latitude=latest_report.latitude,
            longitude=latest_report.longitude,
            accuracy=latest_report.horizontal_accuracy,
            timestamp=latest_report.timestamp,
        )

"""InXPhone (MOR/Kolmisoft) telephony provider service.

Integrates with MOR billing API for:
- Outbound calls via callback_init
- Invoice retrieval
- Recording retrieval
- SIP device status
"""

import hashlib
import xml.etree.ElementTree as ET

import httpx
import structlog

from app.services.telephony.base import CallDirection, CallInfo, CallStatus, PhoneNumber, TelephonyProvider

logger = structlog.get_logger()


class InXPhoneService(TelephonyProvider):
    """InXPhone/MOR billing API integration.

    Uses MOR's callback_init for outbound calls, which works as:
    1. POST callback_init to MOR
    2. MOR calls the customer (src) first
    3. When customer answers, MOR calls our SIP device (dst)
    4. Both legs are bridged
    """

    def __init__(
        self,
        username: str,
        api_key: str,
        device_id: str,
        server_url: str,
        ai_number: str,
    ):
        """Initialize InXPhone service.

        Args:
            username: MOR API username (e.g., "2887777")
            api_key: API secret key used for SHA1 hash computation
            device_id: MOR device ID (e.g., "188444")
            server_url: MOR API base URL (e.g., "http://92.241.68.6/billing/api/")
            ai_number: Our SIP device phone number used as dst (e.g., "995322887777")
        """
        self.username = username
        self.api_key = api_key
        self.device_id = device_id
        self.server_url = server_url.rstrip("/")
        self.ai_number = ai_number
        self._client = httpx.AsyncClient(timeout=30.0)
        self.logger = logger.bind(provider="inxphone")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    # =========================================================================
    # TelephonyProvider ABC implementation
    # =========================================================================

    async def initiate_call(
        self,
        to_number: str,
        from_number: str,
        webhook_url: str,
        agent_id: str | None = None,
    ) -> CallInfo:
        """Initiate an outbound call via MOR callback_init.

        MOR parameter mapping:
            to_number (customer)  -> src (MOR calls this first)
            ai_number (config)    -> dst (our SIP device, MOR calls second)
            from_number (agent)   -> cli_lega (caller ID shown to customer)
            to_number             -> cli_legb (caller ID shown to AI device)
            device_id (config)    -> device
            username (config)     -> u

        Hash formula: SHA1(device + dst + src + apiKey)
        """
        # Compute hash: SHA1(device + dst + src + apiKey)
        hash_value = self._compute_hash(self.device_id, self.ai_number, to_number, self.api_key)

        params = {
            "u": self.username,
            "device": self.device_id,
            "src": to_number,
            "dst": self.ai_number,
            "cli_lega": from_number,
            "cli_legb": to_number,
            "callback_uniqueid": "1",
            "hash": hash_value,
        }

        self.logger.info(
            "initiating_callback",
            src=to_number,
            dst=self.ai_number,
            device=self.device_id,
        )

        response = await self._client.post(
            f"{self.server_url}/callback_init",
            params=params,
        )
        response.raise_for_status()

        root = self._parse_xml(response.text)
        status = root.findtext("status", "")

        if status.lower() != "ok":
            error_msg = root.findtext("status", "Unknown error")
            self.logger.error("callback_init_failed", status=error_msg, response=response.text)
            raise RuntimeError(f"InXPhone callback_init failed: {error_msg}")

        # MOR returns callback_uniqueid in response
        callback_id = root.findtext("callback_uniqueid", "") or root.findtext("uniqueid", "")
        if not callback_id:
            callback_id = f"inx_{to_number}_{self.device_id}"

        self.logger.info("callback_initiated", callback_id=callback_id)

        return CallInfo(
            call_id=callback_id,
            from_number=from_number,
            to_number=to_number,
            direction=CallDirection.OUTBOUND,
            status=CallStatus.INITIATED,
            agent_id=agent_id,
        )

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up a call. Not supported by MOR API."""
        raise NotImplementedError("MOR API does not support remote hangup")

    async def list_phone_numbers(self) -> list[PhoneNumber]:
        """List phone numbers. Managed in MOR admin, returns empty list."""
        return []

    async def search_phone_numbers(
        self,
        country: str = "US",
        area_code: str | None = None,
        contains: str | None = None,
        limit: int = 10,
    ) -> list[PhoneNumber]:
        """Search phone numbers. Not supported by MOR API."""
        raise NotImplementedError("Phone number search not available via MOR API")

    async def purchase_phone_number(self, phone_number: str) -> PhoneNumber:
        """Purchase a phone number. Not supported by MOR API."""
        raise NotImplementedError("Phone number purchase not available via MOR API")

    async def release_phone_number(self, phone_number_id: str) -> bool:
        """Release a phone number. Not supported by MOR API."""
        raise NotImplementedError("Phone number release not available via MOR API")

    def generate_answer_response(self, websocket_url: str, agent_id: str | None = None) -> str:
        """Generate answer response. Not applicable for MOR (FreeSWITCH handles this)."""
        raise NotImplementedError("InXPhone uses FreeSWITCH for call handling, not TwiML/TeXML")

    # =========================================================================
    # InXPhone-specific methods
    # =========================================================================

    async def get_invoices(self, from_ts: int, till_ts: int) -> list[dict]:
        """Get invoices from MOR.

        Args:
            from_ts: Start timestamp (Unix epoch)
            till_ts: End timestamp (Unix epoch)

        Returns:
            List of invoice dictionaries
        """
        hash_value = self._compute_hash(self.api_key)

        params = {
            "u": self.username,
            "from": str(from_ts),
            "till": str(till_ts),
            "hash": hash_value,
        }

        response = await self._client.post(
            f"{self.server_url}/invoices_get",
            params=params,
        )
        response.raise_for_status()

        root = self._parse_xml(response.text)
        invoices = []

        for invoice_el in root.findall(".//invoice"):
            invoice = {child.tag: child.text for child in invoice_el}
            invoices.append(invoice)

        return invoices

    async def get_recordings(
        self,
        date_from: int,
        date_till: int,
        source: str | None = None,
        destination: str | None = None,
    ) -> list[dict]:
        """Get call recordings from MOR.

        Args:
            date_from: Start timestamp (Unix epoch)
            date_till: End timestamp (Unix epoch)
            source: Filter by source number
            destination: Filter by destination number

        Returns:
            List of recording dictionaries
        """
        hash_value = self._compute_hash(self.api_key)

        params: dict[str, str] = {
            "u": self.username,
            "date_from": str(date_from),
            "date_till": str(date_till),
            "hash": hash_value,
        }
        if source:
            params["source"] = source
        if destination:
            params["destination"] = destination

        response = await self._client.post(
            f"{self.server_url}/recordings_get",
            params=params,
        )
        response.raise_for_status()

        root = self._parse_xml(response.text)
        recordings = []

        for rec_el in root.findall(".//recording"):
            recording = {child.tag: child.text for child in rec_el}
            recordings.append(recording)

        return recordings

    async def get_recording_for_call(self, callback_uniqueid: str) -> dict | None:
        """Fetch a specific recording by callback_uniqueid.

        Args:
            callback_uniqueid: The unique call ID from callback_init

        Returns:
            Recording dict or None if not found
        """
        hash_value = self._compute_hash(self.api_key)

        params = {
            "u": self.username,
            "callback_uniqueid": callback_uniqueid,
            "hash": hash_value,
        }

        response = await self._client.post(
            f"{self.server_url}/recordings_get",
            params=params,
        )
        response.raise_for_status()

        root = self._parse_xml(response.text)
        rec_el = root.find(".//recording")

        if rec_el is None:
            return None

        return {child.tag: child.text for child in rec_el}

    async def get_device_details(self) -> dict:
        """Get SIP device details from MOR.

        Returns:
            Device details dict (includes SIP credentials, registration status)
        """
        hash_value = self._compute_hash(self.api_key)

        params = {
            "u": self.username,
            "device": self.device_id,
            "hash": hash_value,
        }

        response = await self._client.get(
            f"{self.server_url}/device_details_get",
            params=params,
        )
        response.raise_for_status()

        root = self._parse_xml(response.text)
        details = {}

        for child in root:
            details[child.tag] = child.text

        return details

    # =========================================================================
    # Private helpers
    # =========================================================================

    @staticmethod
    def _compute_hash(*parts: str) -> str:
        """Compute SHA1 hash of concatenated strings.

        Args:
            *parts: Strings to concatenate and hash

        Returns:
            Hex-encoded SHA1 hash
        """
        combined = "".join(parts)
        return hashlib.sha1(combined.encode()).hexdigest()  # noqa: S324

    @staticmethod
    def _parse_xml(text: str) -> ET.Element:
        """Parse XML response and check for errors.

        Args:
            text: XML response text

        Returns:
            Root XML element

        Raises:
            RuntimeError: If the response contains an error status
        """
        root = ET.fromstring(text)  # noqa: S314

        # Check for MOR error responses
        error = root.findtext("error")
        if error:
            raise RuntimeError(f"MOR API error: {error}")

        return root

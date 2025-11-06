"""API client for Furbulous Cat."""
from __future__ import annotations

import hashlib
import logging
import time
import requests
from typing import Any

from .const import (
    API_BASE_URL,
    API_AUTH_ENDPOINT,
    API_DEVICE_LIST_ENDPOINT,
    API_DEVICE_PROPERTIES_ENDPOINT,
    API_APPID,
    API_VERSION,
    API_PLATFORM,
    API_USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


class FurbulousCatAuthError(Exception):
    """Exception raised for authentication errors."""


class FurbulousCatAPI:
    """API client for Furbulous Cat."""

    def __init__(self, email: str, password: str, account_type: int = 1, token: str | None = None) -> None:
        """Initialize the API client."""
        self.email = email
        self.password = password
        self.account_type = account_type
        self.token = token  # Allow pre-set token
        self.identity_id = None
        self.session = requests.Session()
        self.devices: list[dict[str, Any]] = []

    def _generate_sign(self, timestamp: int, path: str) -> str:
        """Generate signature for API requests.
        
        Algorithm found in decompiled app:
        MD5(appid + url_path + timestamp)
        """
        data = f"{API_APPID}{path}{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()

    def authenticate(self) -> bool:
        """Authenticate with the Furbulous Cat API."""
        url = f"{API_BASE_URL}{API_AUTH_ENDPOINT}"
        
        timestamp = int(time.time())
        sign = self._generate_sign(timestamp, API_AUTH_ENDPOINT)
        
        # DEBUG: Log signature calculation
        _LOGGER.debug("=== SIGNATURE CALCULATION ===")
        _LOGGER.debug("APPID: %s", API_APPID)
        _LOGGER.debug("Endpoint: %s", API_AUTH_ENDPOINT)
        _LOGGER.debug("Timestamp: %s", timestamp)
        sign_input = f"{API_APPID}{API_AUTH_ENDPOINT}{timestamp}"
        _LOGGER.debug("Sign input string: %s", sign_input)
        _LOGGER.debug("Generated sign: %s", sign)
        
        payload = {
            "account_type": 1,
            "area": "1",
            "client_token": "0acd1c78b8d16156bf59970de261cf2666e373c3042d57d94364b21caea31950",
            "iso": "US",
            "password": self.password,
            "clientid": "65l0vltchd0l1q8",
            "brand": "iPhone",
            "account": self.email,
            "AppVersion": "iPhone_26.0.1_2.0.1_202507031750"
        }
        
        headers = {
            "Content-Type": "application/json",
            "appid": API_APPID,
            "version": API_VERSION,
            "accept": "*/*",
            "accept-language": "en",
            "platform": "ios",
            "user-agent": API_USER_AGENT,
            "ts": str(timestamp),
            "sign": sign,
        }

        try:
            _LOGGER.debug("=== AUTHENTICATION REQUEST ===")
            _LOGGER.debug("URL: %s", url)
            _LOGGER.debug("Payload: %s", {**payload, "password": "***"})
            _LOGGER.debug("Headers: %s", headers)
            
            response = self.session.post(url, json=payload, headers=headers, timeout=10)
            
            _LOGGER.debug("Response status code: %s", response.status_code)
            _LOGGER.debug("Response body: %s", response.text)
            
            response.raise_for_status()
            
            data = response.json()
            
            _LOGGER.debug("Authentication response code: %s, message: %s", 
                        data.get("code"), data.get("message"))
            
            if data.get("code") != 0:
                raise FurbulousCatAuthError(f"Authentication failed: {data.get('message')}")
            
            auth_data = data.get("data", {})
            self.token = auth_data.get("token")
            self.identity_id = auth_data.get("identityid")
            
            if not self.token:
                raise FurbulousCatAuthError("No token received from API")
            
            _LOGGER.info("Successfully authenticated with Furbulous Cat API")
            _LOGGER.debug("Token: %s..., Identity ID: %s", self.token[:10] if self.token else None, self.identity_id)
            return True
            
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Error during authentication: %s", err)
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response status: %s, body: %s", 
                            err.response.status_code, err.response.text)
            raise FurbulousCatAuthError(f"Authentication request failed: {err}") from err

    def _get_headers(self, endpoint: str) -> dict:
        """Generate headers for authenticated requests."""
        timestamp = int(time.time())
        sign = self._generate_sign(timestamp, endpoint)
        
        return {
            "Content-Type": "application/json",
            "appid": API_APPID,
            "accept": "*/*",
            "version": API_VERSION,
            "authorization": self.token,
            "accept-language": "en",
            "platform": "ios",  # Use ios instead of android
            "user-agent": API_USER_AGENT,
            "ts": str(timestamp),
            "sign": sign,
        }

    def _make_authenticated_request(self, endpoint: str, method: str = "GET", data: dict[str, Any] | None = None) -> dict:
        """Make an authenticated request to the API.
        
        Args:
            endpoint: Full endpoint URL including query parameters
            method: HTTP method (GET or POST)
            data: JSON data for POST requests
        """
        if not self.token:
            self.authenticate()
        
        url = f"{API_BASE_URL}{endpoint}"
        # Extract path without query parameters for signature
        base_endpoint = endpoint.split('?')[0]
        headers = self._get_headers(base_endpoint)
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = self.session.post(url, headers=headers, json=data or {}, timeout=10)
            elif method == "PUT":
                response = self.session.put(url, headers=headers, json=data or {}, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            result = response.json()
            
            # Check if the response indicates success
            if result.get("code") != 0:
                error_message = result.get("message", "")
                _LOGGER.warning("API returned error code %s: %s", result.get("code"), error_message)
                
                # Check for token expiration/invalid token errors
                # "无效的 Token" = Invalid Token in Chinese
                # Also check for common auth error codes
                is_token_error = (
                    "token" in error_message.lower() or 
                    "无效的" in error_message or  # Invalid in Chinese
                    "Token" in error_message or
                    result.get("code") in [401, 10401, 10402]  # Common auth error codes
                )
                
                if is_token_error:
                    _LOGGER.info("Token expired or invalid, re-authenticating...")
                    self.authenticate()
                    # Retry once with new token
                    headers = self._get_headers(base_endpoint)
                    if method == "GET":
                        response = self.session.get(url, headers=headers, timeout=10)
                    elif method == "POST":
                        response = self.session.post(url, headers=headers, json=data or {}, timeout=10)
                    elif method == "PUT":
                        response = self.session.put(url, headers=headers, json=data or {}, timeout=10)
                    result = response.json()
                    
                    if result.get("code") != 0:
                        _LOGGER.error("Request failed even after re-authentication: %s", result.get("message"))
            
            return result

        except requests.exceptions.RequestException as err:
            _LOGGER.error("Error making authenticated request to %s: %s", endpoint, err)
            
            # Retry authentication if we get a 401
            if hasattr(err, 'response') and err.response is not None and err.response.status_code == 401:
                _LOGGER.info("Got 401 error, re-authenticating...")
                self.authenticate()
                # Retry the request once
                headers = self._get_headers(base_endpoint)
                if method == "GET":
                    response = self.session.get(url, headers=headers, timeout=10)
                elif method == "POST":
                    response = self.session.post(url, headers=headers, json=data or {}, timeout=10)
                elif method == "PUT":
                    response = self.session.put(url, headers=headers, json=data or {}, timeout=10)
                return response.json()
            
            raise

    def get_devices(self) -> list[dict[str, Any]]:
        """Get list of Furbulous devices."""
        try:
            result = self._make_authenticated_request(API_DEVICE_LIST_ENDPOINT)

            if result.get("code") == 0:
                # data is already a list, not a dict with "list" key
                devices_data = result.get("data", [])
                self.devices = devices_data if isinstance(devices_data, list) else []
                _LOGGER.info("Retrieved %d Furbulous devices", len(self.devices))

                # Debug: Log device structure to understand field names
                for idx, device in enumerate(self.devices):
                    _LOGGER.debug("Device %d keys: %s", idx, list(device.keys()))
                    _LOGGER.debug("Device %d sample data: iotid=%s, name fields: %s",
                                idx,
                                device.get("iotid"),
                                {k: device.get(k) for k in device.keys() if 'name' in k.lower()})

                return self.devices
            else:
                _LOGGER.error("Failed to get devices: %s", result.get("message"))
                return []

        except Exception as err:
            _LOGGER.error("Error getting devices: %s", err)
            raise

    def get_device_properties(self, iotid: str) -> dict[str, Any]:
        """Get properties for a specific device.

        Uses the properties/get endpoint which returns all device properties.
        Each property has a 'value' and 'time' field.
        """
        try:
            # Use the properties/get endpoint
            endpoint = f"/app/v1/device/properties/get?iotid={iotid}"
            result = self._make_authenticated_request(endpoint)

            if result.get("code") == 0:
                properties = result.get("data", {})
                # Extract just the values from the properties
                # Each property is a dict with 'value' and 'time'
                extracted_props = {}
                for key, prop_data in properties.items():
                    if isinstance(prop_data, dict) and 'value' in prop_data:
                        extracted_props[key] = prop_data['value']
                    else:
                        extracted_props[key] = prop_data

                _LOGGER.debug("Retrieved %d properties for device %s", len(extracted_props), iotid)

                # Debug: Log sample of property keys to understand what's available
                if extracted_props:
                    all_keys = list(extracted_props.keys())
                    _LOGGER.debug("ALL property keys for %s: %s", iotid, all_keys)

                    # Log some common property values
                    important_keys = [
                        'workstatus', 'catWeight', 'catCleanOnOff',  # Fixed: workstatus is lowercase
                        'errorReportEvent', 'completionStatus', 'handMode',  # Waste bin related
                        'excreteTimesEveryday', 'excreteTimerEveryday'  # Daily usage stats
                    ]
                    for key in important_keys:
                        if key in extracted_props:
                            _LOGGER.debug("Property %s = %s", key, extracted_props[key])

                return extracted_props
            else:
                _LOGGER.warning("Failed to get properties for device %s: %s (code: %s)",
                              iotid, result.get("message"), result.get("code"))
                return {}

        except Exception as err:
            _LOGGER.warning("Error getting properties for device %s: %s", iotid, err)
            # Return empty dict instead of raising - properties are optional
            return {}

    def set_device_property(self, iotid: str, properties: dict[str, Any]) -> bool:
        """Set device properties.
        
        Args:
            iotid: Device IoT ID
            properties: Dict of property_name: value to set
            
        Returns:
            True if successful
            
        Example:
            api.set_device_property("849DC2F4F30B", {"childLockOnOff": 1})
        """
        try:
            endpoint = "/app/v1/device/properties/set"
            payload = {
                "iotid": iotid,
                **properties
            }
            
            result = self._make_authenticated_request(endpoint, method="POST", data=payload)
            
            if result.get("code") == 0:
                _LOGGER.info("Successfully set properties for %s: %s", iotid, properties)
                return True
            else:
                _LOGGER.error("Failed to set properties for %s: %s", iotid, result.get("message"))
                return False
                
        except Exception as err:
            _LOGGER.error("Error setting properties for %s: %s", iotid, err)
            return False

    def set_device_disturb(self, iotid: str, is_disturb: bool) -> bool:
        """Set device Do Not Disturb mode.
        
        Args:
            iotid: Device IoT ID
            is_disturb: True to enable DND, False to disable
            
        Returns:
            True if successful
        """
        try:
            endpoint = "/app/v1/device/disturb"
            payload = {
                "iotid": iotid,
                "is_disturb": 1 if is_disturb else 0
            }
            
            result = self._make_authenticated_request(endpoint, method="PUT", data=payload)
            
            if result.get("code") == 0:
                _LOGGER.info("Successfully set DND mode for %s: %s", iotid, is_disturb)
                return True
            else:
                _LOGGER.error("Failed to set DND mode for %s: %s", iotid, result.get("message"))
                return False
                
        except Exception as err:
            _LOGGER.error("Error setting DND mode for %s: %s", iotid, err)
            return False

    def get_pets(self) -> list[dict[str, Any]]:
        """Get list of all pets.
        
        Returns:
            List of pet dictionaries
        """
        try:
            endpoint = "/app/v1/pet/list"
            result = self._make_authenticated_request(endpoint)
            
            if result.get("code") == 0:
                pets_data = result.get("data", {})
                # The API returns {data: {list: [...]}}
                if isinstance(pets_data, dict):
                    pets = pets_data.get("list", [])
                else:
                    pets = []
                _LOGGER.info("Retrieved %d pets", len(pets))
                return pets
            else:
                _LOGGER.error("Failed to get pets: %s", result.get("message"))
                return []
                
        except Exception as err:
            _LOGGER.error("Error getting pets: %s", err)
            return []

    def get_pet_info(self, pet_id: int) -> dict[str, Any]:
        """Get detailed information for a specific pet.
        
        Args:
            pet_id: Pet ID
            
        Returns:
            Dict with pet information
        """
        try:
            endpoint = f"/app/v1/pet/info?petid={pet_id}"
            result = self._make_authenticated_request(endpoint)
            
            if result.get("code") == 0:
                pet_info = result.get("data", {})
                _LOGGER.debug("Retrieved info for pet %s", pet_id)
                return pet_info if isinstance(pet_info, dict) else {}
            else:
                _LOGGER.warning("Failed to get info for pet %s: %s", pet_id, result.get("message"))
                return {}
                
        except Exception as err:
            _LOGGER.warning("Error getting info for pet %s: %s", pet_id, err)
            return {}

    def get_data(self) -> dict[str, Any]:
        """Get data from the Furbulous Cat API."""
        _LOGGER.debug("=== API get_data() called ===")

        devices = self.get_devices()
        _LOGGER.debug("Retrieved %d devices", len(devices))

        # Get properties for each device
        devices_with_properties = []
        for device in devices:
            iotid = device.get("iotid")
            device_name = device.get("name", "Unknown")  # Fixed: use 'name' not 'devicename'
            if iotid:
                _LOGGER.debug("Fetching properties for device: %s (iotid: %s)", device_name, iotid)
                properties = self.get_device_properties(iotid)
                device["properties"] = properties
                _LOGGER.debug("Device %s has %d properties", device_name, len(properties))
            devices_with_properties.append(device)

        # Get pets information
        pets = self.get_pets()
        _LOGGER.debug("Retrieved %d pets", len(pets))

        # No need to get detailed info, /pet/list already returns everything

        return {
            "authenticated": True,
            "token": self.token,
            "identity_id": self.identity_id,
            "devices": devices_with_properties,
            "pets": pets,
        }

# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
#
# Author:
# Aleksander Bydłowski
# abydlowski@theodyss.ai
# aleksander.bydlowski@gmail.com
import os
import re
from typing import Any, Optional

from dotenv import load_dotenv, find_dotenv

from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.appconfiguration.aio import AzureAppConfigurationClient
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError, HttpResponseError

from odyss_ai_flows.core.utils.logger import logger


# ----------------------------
# Load dotenv (local dev)
# ----------------------------

load_dotenv(find_dotenv(".env.local"))


# ----------------------------
# Shared base provider
# ----------------------------

class _AzureBaseProvider:
    def __init__(self):
        self._cache: dict[str, Any] = {}

    def _get_env(self, key: str) -> Optional[str]:
        return os.getenv(key)

    def _get_cached(self, key: str) -> tuple[bool, Any]:
        if key in self._cache:
            return True, self._cache[key]
        return False, None

    def _set_cache(self, key: str, value: Any):
        self._cache[key] = value

    def _log_exception(self, msg: str):
        logger.exception(msg)


# ----------------------------
# Azure Config Provider
# ----------------------------

_KV_REF_PATTERN = re.compile(
    r"^@Microsoft\.KeyVault\(SecretUri=(?P<uri>[^)]+)\)$")


class AzureConfigProvider(_AzureBaseProvider):
    def __init__(self):
        super().__init__()

        self._credential: Optional[DefaultAzureCredential] = None
        self._client: Optional[AzureAppConfigurationClient] = None
        self._endpoint: Optional[str] = None

        # reuse KV clients per vault
        self._kv_clients: dict[str, SecretClient] = {}

    async def __call__(self, key: str) -> Any:
        # ENV override
        env_val = self._get_env(key)
        if env_val is not None:
            return env_val

        # cache
        cached, value = self._get_cached(key)
        if cached:
            return value

        await self._ensure_client()

        if not self._client:
            raise RuntimeError("AZURE_APP_CONFIG_ENDPOINT not configured")

        try:
            setting = await self._client.get_configuration_setting(key=key)
            value = setting.value

            if value:
                value = await self._resolve_kv_reference(value)

            self._set_cache(key, value)
            return value

        except ResourceNotFoundError:
            self._set_cache(key, None)
            return None

        except ClientAuthenticationError:
            self._log_exception(
                "Authentication failed when accessing Azure App Configuration")
            raise

        except HttpResponseError:
            self._log_exception(
                "HTTP error when accessing Azure App Configuration")
            raise

        except Exception:
            self._log_exception(
                "Unexpected error accessing Azure App Configuration")
            raise

    async def _ensure_client(self):
        if self._client:
            return

        if not self._endpoint:
            try:
                from odyss_ai_flows.core.config.global_config import get_global_setting
                self._endpoint = await get_global_setting("AZURE_APP_CONFIG_ENDPOINT")
            except Exception:
                pass

        endpoint = self._endpoint or os.getenv("AZURE_APP_CONFIG_ENDPOINT")

        if not endpoint:
            return

        self._credential = DefaultAzureCredential()
        self._client = AzureAppConfigurationClient(
            base_url=endpoint,
            credential=self._credential,
        )

    async def _resolve_kv_reference(self, value: str) -> Any:
        match = _KV_REF_PATTERN.match(value)
        if not match:
            return value  # normal value

        if not self._credential:
            raise RuntimeError(
                "Credential not initialized for Key Vault resolution")

        uri = match.group("uri")

        # strict parsing
        try:
            base, rest = uri.split("/secrets/")
            name = rest.split("/")[0]
        except Exception:
            raise RuntimeError(f"Invalid Key Vault reference format: {value}")

        # reuse or create client
        client = self._kv_clients.get(base)
        if not client:
            client = SecretClient(vault_url=base, credential=self._credential)
            self._kv_clients[base] = client

        try:
            secret = await client.get_secret(name)
            return secret.value

        except ResourceNotFoundError:
            raise RuntimeError(
                f"Referenced Key Vault secret '{name}' not found in '{base}'")

        except ClientAuthenticationError:
            self._log_exception(
                "Authentication failed when accessing Azure Key Vault (via App Config)")
            raise

        except HttpResponseError:
            self._log_exception(
                "HTTP error when accessing Azure Key Vault (via App Config)")
            raise

        except Exception:
            self._log_exception(
                "Unexpected error resolving Key Vault reference")
            raise


# ----------------------------
# Azure Secret Provider
# ----------------------------

class AzureSecretProvider(_AzureBaseProvider):
    def __init__(self):
        super().__init__()

        self._credential: Optional[DefaultAzureCredential] = None
        self._client: Optional[SecretClient] = None
        self._kv_url: Optional[str] = None

    async def __call__(self, key: str) -> Any:
        # ENV override
        env_val = self._get_env(key)
        if env_val is not None:
            return env_val

        # cache
        cached, value = self._get_cached(key)
        if cached:
            return value

        await self._ensure_client()

        if not self._client:
            raise RuntimeError("AZURE_KEY_VAULT_URL not configured")

        try:
            secret = await self._client.get_secret(key)
            value = secret.value

            self._set_cache(key, value)
            return value

        except ResourceNotFoundError:
            self._set_cache(key, None)
            return None

        except ClientAuthenticationError:
            self._log_exception(
                "Authentication failed when accessing Azure Key Vault")
            raise

        except HttpResponseError:
            self._log_exception("HTTP error when accessing Azure Key Vault")
            raise

        except Exception:
            self._log_exception("Unexpected error accessing Azure Key Vault")
            raise

    async def _ensure_client(self):
        if self._client:
            return

        if not self._kv_url:
            try:
                from odyss_ai_flows.core.config.global_config import get_global_setting
                self._kv_url = await get_global_setting("AZURE_KEY_VAULT_URL")
            except Exception:
                pass

        kv_url = self._kv_url or os.getenv("AZURE_KEY_VAULT_URL")

        if not kv_url:
            return

        self._credential = DefaultAzureCredential()
        self._client = SecretClient(
            vault_url=kv_url,
            credential=self._credential,
        )

from collections import defaultdict
from functools import _make_key # noqa
from threading import Lock
from typing import Optional, List, Dict, Any

import httpx
from cachetools import cached, TTLCache

from sap.xssec.constants import HTTP_TIMEOUT_IN_SECONDS, KEYCACHE_DEFAULT_CACHE_SIZE, \
    KEYCACHE_DEFAULT_CACHE_ENTRY_EXPIRATION_TIME_IN_MINUTES
from sap.xssec.key_tools import jwk_to_pem

default_cache_policy = cached(cache=TTLCache(
    maxsize=KEYCACHE_DEFAULT_CACHE_SIZE, ttl=KEYCACHE_DEFAULT_CACHE_ENTRY_EXPIRATION_TIME_IN_MINUTES * 60))


def thread_safe_by_args(func):
    lock_dict = defaultdict(Lock)

    def _thread_safe_func(*args, **kwargs):
        key = _make_key(args, kwargs, typed=False)
        with lock_dict[key]:
            return func(*args, **kwargs)

    return _thread_safe_func


def _fetch_verification_key_url_ias(issuer_url: str) -> str:
    resp = httpx.get(issuer_url + '/.well-known/openid-configuration', headers={'Accept': 'application/json'},
                     timeout=HTTP_TIMEOUT_IN_SECONDS)
    resp.raise_for_status()
    return resp.json()["jwks_uri"]


def _download_verification_key_ias(verification_key_url: str, zone_id: Optional[str]) -> List[Dict[str, Any]]:
    default_headers = {'Accept': 'application/json'}
    headers = default_headers if zone_id is None else {**default_headers, "x-zone_uuid": zone_id}
    resp = httpx.get(verification_key_url, headers=headers, timeout=HTTP_TIMEOUT_IN_SECONDS)
    resp.raise_for_status()
    return resp.json()["keys"]


@thread_safe_by_args
@default_cache_policy
def get_verification_key_ias(issuer_url: str, zone_id: Optional[str], kid: str) -> str:
    verification_key_url: str = _fetch_verification_key_url_ias(issuer_url)
    verification_key_list: List[Dict[str, Any]] = _download_verification_key_ias(verification_key_url, zone_id)
    found = list(filter(lambda k: k["kid"] == kid, verification_key_list))
    if len(found) == 0:
        raise ValueError("Could not find key with kid {}".format(kid))
    return jwk_to_pem(found[0])


@thread_safe_by_args
@default_cache_policy
def get_verification_key_xsuaa(jku: str, kid: str) -> str:
    # TODO
    raise NotImplementedError()

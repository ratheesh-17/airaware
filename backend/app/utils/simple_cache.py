# backend/app/utils/simple_cache.py
import time

_cache = {}

def set_cache(key: str, value, ttl: int = 300):
    _cache[key] = (time.time() + ttl, value)

def get_cache(key: str):
    rec = _cache.get(key)
    if not rec:
        return None
    expires, val = rec
    if time.time() > expires:
        del _cache[key]
        return None
    return val


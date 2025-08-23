# backend/app/utils/simple_cache.py
import time
import threading

_cache = {}
_lock = threading.Lock()

def set_cache(key: str, value, ttl: int = 300):
    expires = time.time() + ttl
    with _lock:
        _cache[key] = (expires, value)

def get_cache(key: str):
    with _lock:
        rec = _cache.get(key)
        if not rec:
            return None
        expires, val = rec
        if time.time() > expires:
            del _cache[key]
            return None
        return val

def clear_cache():
    with _lock:
        _cache.clear()

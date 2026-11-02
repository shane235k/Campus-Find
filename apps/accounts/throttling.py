"""Login attempt throttling and rate limiting utility."""
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes


def get_client_ip(request):
    """Safely extracts client IP address from request headers."""
    if not request:
        return "127.0.0.1"
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
    return ip


def get_throttle_cache_key(identifier):
    """Generates a cache key for tracking login failures."""
    return f"login_throttle:{identifier.strip().lower()}"


def is_rate_limited(request, identifier=""):
    """Checks whether the given IP or email identifier is currently throttled."""
    ip = get_client_ip(request)
    ip_key = get_throttle_cache_key(f"ip_{ip}")
    id_key = get_throttle_cache_key(f"id_{identifier}") if identifier else None

    ip_attempts = cache.get(ip_key, 0)
    id_attempts = cache.get(id_key, 0) if id_key else 0

    if ip_attempts >= MAX_FAILED_ATTEMPTS or id_attempts >= MAX_FAILED_ATTEMPTS:
        return True
    return False


def record_failed_attempt(request, identifier=""):
    """Increments the failed login attempt counter."""
    ip = get_client_ip(request)
    ip_key = get_throttle_cache_key(f"ip_{ip}")
    
    current_ip = cache.get(ip_key, 0) + 1
    cache.set(ip_key, current_ip, LOCKOUT_DURATION_SECONDS)

    if identifier:
        id_key = get_throttle_cache_key(f"id_{identifier}")
        current_id = cache.get(id_key, 0) + 1
        cache.set(id_key, current_id, LOCKOUT_DURATION_SECONDS)

    logger.warning("Failed login attempt from IP %s for identifier '%s'", ip, identifier)


def reset_throttle(request, identifier=""):
    """Resets failed attempt counters upon successful authentication."""
    ip = get_client_ip(request)
    cache.delete(get_throttle_cache_key(f"ip_{ip}"))
    if identifier:
        cache.delete(get_throttle_cache_key(f"id_{identifier}"))

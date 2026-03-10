"""
Simple in-memory rate limiting for local application

This is a lightweight rate limiter appropriate for a local-only application.
For production web applications, consider Redis-backed rate limiting.
"""

import time
import threading
from collections import defaultdict
from functools import wraps
from typing import Optional, Callable

from flask import request, g

from .responses import api_error


class RateLimiter:
    """
    Thread-safe in-memory rate limiter using sliding window algorithm.

    Appropriate for local applications where requests come from localhost only.
    """

    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum sustained requests per minute
            burst_limit: Maximum requests allowed in a short burst (1 second)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self._lock = threading.Lock()
        self._request_times = defaultdict(list)
        self._cleanup_interval = 60  # Cleanup old entries every 60 seconds
        self._last_cleanup = time.time()

    def is_allowed(self, key: str = "default") -> bool:
        """
        Check if a request is allowed under rate limits.

        Args:
            key: Identifier for the rate limit bucket (e.g., IP address, endpoint)

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()

        with self._lock:
            # Periodic cleanup
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup(now)

            # Get request history for this key
            times = self._request_times[key]

            # Remove requests older than 1 minute
            cutoff_minute = now - 60
            self._request_times[key] = [t for t in times if t > cutoff_minute]
            times = self._request_times[key]

            # Check per-minute rate limit
            if len(times) >= self.requests_per_minute:
                return False

            # Check burst rate limit (requests in last second)
            cutoff_second = now - 1
            recent_requests = sum(1 for t in times if t > cutoff_second)
            if recent_requests >= self.burst_limit:
                return False

            # Record this request
            self._request_times[key].append(now)
            return True

    def _cleanup(self, now: float) -> None:
        """Remove old entries to prevent memory growth"""
        cutoff = now - 120  # Remove entries older than 2 minutes
        keys_to_remove = []

        for key, times in self._request_times.items():
            self._request_times[key] = [t for t in times if t > cutoff]
            if not self._request_times[key]:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._request_times[key]

        self._last_cleanup = now

    def get_stats(self, key: str = "default") -> dict:
        """Get rate limit statistics for debugging"""
        now = time.time()
        with self._lock:
            times = self._request_times.get(key, [])
            cutoff_minute = now - 60
            recent = [t for t in times if t > cutoff_minute]

            return {
                'key': key,
                'requests_last_minute': len(recent),
                'limit_per_minute': self.requests_per_minute,
                'burst_limit': self.burst_limit,
            }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            requests_per_minute=120,  # Generous for local app
            burst_limit=20            # Allow some burst for UI refresh
        )
    return _rate_limiter


def rate_limit(
    requests_per_minute: Optional[int] = None,
    burst_limit: Optional[int] = None,
    key_func: Optional[Callable] = None
):
    """
    Decorator to apply rate limiting to a route.

    Args:
        requests_per_minute: Override default rate limit
        burst_limit: Override default burst limit
        key_func: Function to generate rate limit key (default: endpoint name)

    Usage:
        @app.route('/api/endpoint')
        @rate_limit(requests_per_minute=30)
        def my_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = get_rate_limiter()

            # Generate rate limit key
            if key_func:
                key = key_func()
            else:
                key = request.endpoint or request.path

            # Check rate limit
            if not limiter.is_allowed(key):
                stats = limiter.get_stats(key)
                return api_error(
                    "Rate limit exceeded. Please slow down.",
                    code="RATE_LIMITED",
                    details={
                        'requests_last_minute': stats['requests_last_minute'],
                        'limit': stats['limit_per_minute'],
                    },
                    status_code=429
                )

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def apply_global_rate_limit(app):
    """
    Apply global rate limiting to all API endpoints.

    This is less restrictive than per-endpoint limits but provides
    basic protection against runaway requests.

    Args:
        app: Flask application
    """
    limiter = get_rate_limiter()

    @app.before_request
    def check_global_rate_limit():
        # Only rate limit API endpoints
        if not request.path.startswith('/api/'):
            return None

        # Use endpoint as key for more granular limiting
        key = f"global:{request.endpoint or request.path}"

        if not limiter.is_allowed(key):
            stats = limiter.get_stats(key)
            response, status = api_error(
                "Rate limit exceeded. Please slow down.",
                code="RATE_LIMITED",
                details={
                    'requests_last_minute': stats['requests_last_minute'],
                    'limit': stats['limit_per_minute'],
                    'retry_after': 5,  # Suggest retry in 5 seconds
                },
                status_code=429
            )
            response.headers['Retry-After'] = '5'
            return response, status

        return None

from slowapi import Limiter
from slowapi.util import get_remote_address

from config import get_settings

# Shared limiter instance. Applied to endpoints that are realistic brute-force
# targets: login (password guessing) and join-request submission (access-key
# guessing). Keyed by client IP, which is adequate for a single-instance
# deployment; a shared store (e.g. Redis) would be needed behind multiple
# backend instances.
#
# Disabled under the test environment: slowapi's in-memory store keys on
# client IP, and FastAPI's TestClient reports the same fake address for every
# request, so limits would trip across unrelated tests sharing one process
# rather than reflecting real per-client abuse.
limiter = Limiter(key_func=get_remote_address, enabled=not get_settings().is_test)

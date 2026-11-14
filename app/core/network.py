from starlette.requests import Request


def get_client_ip(request: Request | None) -> str:
    """Extract the real client IP address considering reverse proxies.

    Evaluates headers in the following priority:
    1. CF-Connecting-IP (Cloudflare Edge)
    2. X-Real-IP (Nginx / direct reverse proxy)
    3. X-Forwarded-For (First non-empty comma-separated client IP)
    4. request.client.host (Direct TCP socket peer)
    """
    if not request:
        return "unknown"

    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip and x_real_ip.strip():
        return x_real_ip.strip()

    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for and x_forwarded_for.strip():
        ips = [ip.strip() for ip in x_forwarded_for.split(",") if ip.strip()]
        if ips:
            return ips[0]

    if request.client and request.client.host:
        return request.client.host

    return "unknown"

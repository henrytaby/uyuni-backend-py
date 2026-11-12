from starlette.requests import Request

from app.core.network import get_client_ip


def _make_dummy_request(
    headers: dict[str, str] | None = None,
    client_host: str | None = None,
) -> Request:
    raw_headers = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


def test_get_client_ip_none():
    assert get_client_ip(None) == "unknown"


def test_get_client_ip_fallback_to_client_host():
    req = _make_dummy_request(client_host="192.168.1.50")
    assert get_client_ip(req) == "192.168.1.50"


def test_get_client_ip_no_headers_no_client():
    req = _make_dummy_request()
    assert get_client_ip(req) == "unknown"


def test_get_client_ip_x_forwarded_for_single():
    req = _make_dummy_request(
        headers={"x-forwarded-for": "181.115.167.206"},
        client_host="10.27.232.133",
    )
    assert get_client_ip(req) == "181.115.167.206"


def test_get_client_ip_x_forwarded_for_chain():
    req = _make_dummy_request(
        headers={"x-forwarded-for": "181.115.167.206, 10.27.232.133, 10.29.6.5"},
        client_host="10.27.232.133",
    )
    assert get_client_ip(req) == "181.115.167.206"


def test_get_client_ip_x_real_ip():
    req = _make_dummy_request(
        headers={"x-real-ip": "181.115.167.206"},
        client_host="10.0.0.1",
    )
    assert get_client_ip(req) == "181.115.167.206"


def test_get_client_ip_cf_connecting_ip():
    req = _make_dummy_request(
        headers={
            "cf-connecting-ip": "181.115.167.206",
            "x-real-ip": "172.68.1.1",
            "x-forwarded-for": "181.115.167.206, 172.68.1.1",
        },
        client_host="10.0.0.1",
    )
    assert get_client_ip(req) == "181.115.167.206"

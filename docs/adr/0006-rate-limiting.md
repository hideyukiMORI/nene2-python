# ADR-0006 — Rate Limiting: Fixed Window, In-Memory

Date: 2026-05-19  
Status: Accepted

## Context

We need to protect endpoints from abuse and runaway clients. PHP NENE2's `ThrottleMiddleware` uses a fixed-window strategy stored in PHP session / APCu. For Python we need a simple default with a clear upgrade path.

## Decision

- **Fixed-window algorithm**: count requests per IP per time window (default: 60 req / 60 s)
- **Storage**: in-process `dict` protected by `threading.Lock` — zero dependencies, zero config
- **Key**: `X-Forwarded-For` first entry (when present) else `request.client.host`
- **429 response**: RFC 9457 Problem Details with `Retry-After` header (seconds until window resets)
- **Disabled by default in tests**: `AppSettings(throttle_enabled=False)` — tests create isolated apps with explicit `ThrottleMiddleware(limit=N)`

## Consequences

- Suitable for single-process deployments (uvicorn workers share no state between processes)
- For multi-process / multi-node deployments, replace the in-memory store with Redis (implement `ThrottleStoreInterface` — future work)
- Fixed-window is vulnerable to burst at window boundary; sliding-log or token-bucket can be added later without changing the interface

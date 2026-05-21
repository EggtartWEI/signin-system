# MLPS 2.0 Alignment Notes

This document summarizes how the current service aligns with key MLPS 2.0 (Level 2) controls and what operational steps are still required.

## Implemented in code

- Identity authentication: strict input validation, RSA encrypted credential forwarding, login failure handling.
- Access control (basic): origin checking for /api/login and optional CORS allowlist.
- Security audit: JSON audit log with request ID, user ID, IP, user agent, result, and reason.
- Protection against brute-force: rate limiting and lockout window.
- Secure defaults: minimal error messages, no HTML content returned by default, security headers.
- Availability safeguards: request body size limit, outbound timeout to OA portal.

## Operational requirements (deploy time)

- Enforce HTTPS/TLS 1.2+ at the edge (reverse proxy or load balancer).
- Configure log retention and access control for audit logs (recommended 90 days).
- Centralize logs to a secure log server for tamper resistance.
- Enable time synchronization (NTP) for accurate audit timestamps.
- Apply OS hardening and least privilege for the runtime account.
- Regular vulnerability patching for Python and system dependencies.

## Recommended environment variables

See .env.example for the security-related switches and defaults.

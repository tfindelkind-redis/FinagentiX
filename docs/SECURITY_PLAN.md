# FinagentiX Security Plan

## Overview

This document outlines the security implementation plan for protecting the publicly accessible FinagentiX application from unauthorized access and abuse.

## Current Exposure

| Component | URL | Risk Level |
|-----------|-----|------------|
| **Frontend** | `https://ca-frontend-3ae172dc9e9da.redflower-348a14ef.westus3.azurecontainerapps.io` | 🔴 High - Anyone can access UI |
| **API** | `https://ca-agent-api-3ae172dc9e9da.redflower-348a14ef.westus3.azurecontainerapps.io` | 🔴 High - Anyone can call endpoints directly |

### Why Both Need Protection

Someone could bypass the frontend and call the API directly using curl or any HTTP client, consuming:
- Azure OpenAI API quota ($$)
- Redis Enterprise resources
- Compute resources

---

## Authentication Options

### Option A: Simple Basic Auth (Quick & Easy)

**How it works:**
- Single shared username/password stored as environment variables
- Frontend prompts for credentials on load
- Credentials sent with each API request via `Authorization: Basic` header

**Pros:**
- ✅ Simple to implement (~1 hour)
- ✅ No database needed
- ✅ Works immediately

**Cons:**
- ❌ No user tracking/analytics
- ❌ Credentials in every request
- ❌ Hard to revoke access (must change password)
- ❌ No session management

**Best for:** Quick demo protection

---

### Option B: Session-Based Auth (Recommended)

**How it works:**
1. User enters credentials on login page
2. API validates credentials → returns JWT token
3. Token stored in browser (localStorage or cookie)
4. Token sent with each API request via `Authorization: Bearer` header
5. API validates token on protected routes

**Pros:**
- ✅ Better user experience (login once)
- ✅ Can add rate limiting per session
- ✅ Token expiration for security
- ✅ Can track usage per session
- ✅ Easy to invalidate tokens

**Cons:**
- ❌ Slightly more complex (~3 hours)
- ❌ Requires JWT secret management

**Best for:** Production-ready demo with good UX

---

### Option C: Azure Easy Auth (Azure-Native)

**How it works:**
- Enable built-in authentication on Azure Container Apps
- Supports Microsoft Entra ID, GitHub, Google OAuth
- Zero code changes required

**Pros:**
- ✅ Enterprise-grade security
- ✅ No code changes to API
- ✅ Supports SSO
- ✅ Managed by Azure

**Cons:**
- ❌ Requires Azure AD setup
- ❌ Overkill for demo purposes
- ❌ More complex configuration
- ❌ Users need Microsoft/GitHub/Google account

**Best for:** Enterprise deployments

---

## Recommended Implementation: Option B (Session-Based)

Best balance of security, simplicity, and user experience for a demo application.

### Implementation Plan

#### Phase 1: API Authentication (~1.5 hours)

**File: `src/api/main.py`**

```python
# New dependencies needed:
# - python-jose[cryptography]  (JWT handling)
# - passlib[bcrypt]  (password hashing)

# New endpoints:
POST /api/auth/login     # Validates credentials, returns JWT
POST /api/auth/logout    # Invalidates token (optional)
GET  /api/auth/verify    # Verifies token is valid

# Middleware:
- Add dependency injection for token validation
- Apply to all routes EXCEPT:
  - /api/health (Azure health probes)
  - /api/auth/* (login endpoints)
  - /docs, /openapi.json (optional: keep for development)
```

**Environment Variables:**
```bash
AUTH_USERNAME=admin              # Login username
AUTH_PASSWORD=<secure-password>  # Login password (hashed in production)
JWT_SECRET=<random-32-char>      # Secret for signing tokens
JWT_EXPIRY_HOURS=24              # Token expiration time
```

#### Phase 2: Frontend Login (~1 hour)

**New files:**
- `frontend/src/components/auth/LoginModal.tsx` - Login form component
- `frontend/src/contexts/AuthContext.tsx` - Auth state management
- `frontend/src/utils/api.ts` - API client with auth headers

**Changes:**
- Wrap app in `AuthProvider`
- Show login modal if not authenticated
- Add token to all API requests
- Handle 401 responses (redirect to login)
- Add logout button to header

#### Phase 3: Infrastructure (~30 min)

**Files to update:**
- `infra/stage1-api.bicep` - Add auth env vars
- `scripts/update-api-fast.sh` - Include auth vars in deployment
- `.env.example` - Document new variables

#### Phase 4: Rate Limiting (Optional, ~1 hour)

**Using Redis for rate limiting:**
```python
# Per-IP rate limiting (unauthenticated attempts)
- 5 login attempts per minute
- 10 requests per minute to any endpoint

# Per-session rate limiting (authenticated)
- 100 requests per minute
- 1000 requests per hour
```

---

## Security Checklist

| Item | Priority | Status | Notes |
|------|----------|--------|-------|
| API authentication middleware | 🔴 High | ✅ Done | `src/api/auth.py` + middleware in `main.py` |
| Frontend login page | 🔴 High | ✅ Done | `LoginModal.tsx` + `AuthContext.tsx` |
| JWT token expiration | 🟡 Medium | ✅ Done | 24h default (configurable via `JWT_EXPIRY_HOURS`) |
| HTTPS only | 🟢 Low | ✅ Done | Azure Container Apps default |
| CORS restrictions | 🟡 Medium | ⬜ TODO | Limit API to frontend origin |
| Health endpoint exclusion | 🔴 High | ✅ Done | `/health` endpoint has no auth |
| Rate limiting | 🟡 Medium | ⬜ TODO | Prevents quota exhaustion |
| Password hashing | 🟡 Medium | ✅ Done | bcrypt via passlib |
| Secure headers | 🟢 Low | ⬜ TODO | X-Frame-Options, CSP, etc. |

---

## ✅ Implementation Complete (January 2026)

### Files Created/Modified:
- `src/api/auth.py` - JWT authentication module
- `src/api/main.py` - Auth endpoints + protected routes
- `requirements.txt` - Added `python-jose`, `passlib[bcrypt]`
- `frontend/src/contexts/AuthContext.tsx` - Auth state management
- `frontend/src/components/auth/LoginModal.tsx` - Login UI
- `frontend/src/components/auth/LoginModal.css` - Login styles
- `frontend/src/lib/api.ts` - Auth headers injection
- `frontend/src/App.tsx` - Auth gate
- `frontend/src/main.tsx` - AuthProvider wrapper
- `frontend/src/components/Header.tsx` - Logout button
- `frontend/src/components/RedisBenefits.tsx` - Auth headers

### Default Credentials (Demo):
- Username: `admin`
- Password: **Set via `AUTH_PASSWORD` env var** (required, not stored in git!)

### Environment Variables (REQUIRED):
```bash
AUTH_USERNAME=admin                    # Login username (default: admin)
AUTH_PASSWORD=<your-secure-password>   # REQUIRED - not stored in git!
JWT_SECRET=<random-32-byte-hex>        # REQUIRED - generate with: openssl rand -hex 32
JWT_EXPIRY_HOURS=24                    # Token expiration time (default: 24h)
```

---

## Estimated Effort

| Task | Time Estimate |
|------|---------------|
| API auth middleware + login endpoint | 1.5 hours |
| Frontend login component + auth context | 1 hour |
| Infrastructure env vars (Bicep + scripts) | 30 min |
| Testing & debugging | 30 min |
| Rate limiting (optional) | 1 hour |
| **Total (without rate limiting)** | **~3.5 hours** |
| **Total (with rate limiting)** | **~4.5 hours** |

---

## Configuration Decisions Needed

Before implementation, decide on:

1. **Single user or multiple users?**
   - Single shared password (simpler)
   - Multiple users with individual accounts (more complex)

2. **Token expiry duration?**
   - 24 hours (recommended for demos)
   - 7 days (more convenient)
   - No expiry (less secure)

3. **Benchmark page access?**
   - Require authentication (recommended)
   - Allow limited unauthenticated access

4. **Rate limiting?**
   - Implement now (more protection)
   - Add later (faster initial deployment)

5. **Debug endpoints (`/api/debug/*`)?**
   - Require authentication (recommended)
   - Remove entirely in production
   - Keep open for troubleshooting

---

## API Endpoint Protection Matrix

| Endpoint | Auth Required | Rate Limit | Notes |
|----------|---------------|------------|-------|
| `GET /api/health` | ❌ No | None | Azure health probes |
| `POST /api/auth/login` | ❌ No | 5/min/IP | Prevent brute force |
| `POST /api/auth/logout` | ✅ Yes | None | |
| `GET /api/auth/verify` | ✅ Yes | None | |
| `POST /api/query` | ✅ Yes | 100/min | Main query endpoint |
| `POST /api/query/enhanced` | ✅ Yes | 100/min | Enhanced query |
| `GET /api/cache/*` | ✅ Yes | None | Cache management |
| `POST /api/cache/*/clear` | ✅ Yes | 10/min | Destructive operation |
| `GET /api/debug/*` | ✅ Yes | None | Debug endpoints |
| `GET /docs` | ⚙️ Configurable | None | OpenAPI docs |

---

## Implementation Order

```
1. Add JWT dependencies to requirements.txt
2. Create auth module (src/api/auth.py)
3. Add auth middleware to main.py
4. Test API auth with curl
5. Create frontend LoginModal component
6. Create AuthContext provider
7. Update API client to include token
8. Test full flow
9. Update infrastructure (Bicep, scripts)
10. Deploy and verify
11. (Optional) Add rate limiting
```

---

## Post-Implementation Verification

After implementing, verify:

```bash
# 1. Unauthenticated request should fail
curl https://API_URL/api/query/enhanced \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
# Expected: 401 Unauthorized

# 2. Health endpoint should work without auth
curl https://API_URL/api/health
# Expected: 200 OK

# 3. Login should return token
curl https://API_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "xxx"}'
# Expected: {"token": "eyJ..."}

# 4. Authenticated request should work
curl https://API_URL/api/query/enhanced \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{"query": "AAPL price"}'
# Expected: 200 OK with response
```

---

## References

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Azure Container Apps Authentication](https://learn.microsoft.com/en-us/azure/container-apps/authentication)
- [JWT Best Practices](https://auth0.com/blog/jwt-security-best-practices/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)

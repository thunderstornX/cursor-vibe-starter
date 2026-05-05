# 06 — JWT authentication flow

## Context

Use this when wiring auth into a FastAPI service for the first time, or
porting an existing service from API-key auth to bearer-token JWT.
This is the prompt where AI tools most enthusiastically reinvent the
universe — be sceptical of everything.

## Template

```
Implement JWT bearer authentication for a FastAPI service. Output:

  1. `auth.py` with:
     - mint_jwt(sub: str, expire_minutes: int) -> str
     - decode_jwt(token: str) -> JwtPayload (raises on expired or
       invalid signature; refuses alg=none)
     - get_current_user(token: str = Depends(...)) -> User
  2. `routes/auth.py` with POST /v1/auth/login that validates a
     username/password against the user table and returns a token
  3. A pytest suite covering:
     - happy path login
     - wrong password rejection (constant-time, no user enumeration)
     - expired token rejection
     - tampered token rejection
     - alg=none token rejection

Constraints:
  - HS256 only; algorithms=[ALGORITHM] explicitly
  - Read JWT_SECRET from env via pydantic-settings; refuse to start
    if it's missing or shorter than 32 bytes
  - Password hash: bcrypt (12 rounds)
  - Token expiry: 60 minutes default, 5 minutes minimum
  - Login response payload contains ONLY {access_token, token_type:
    "bearer", expires_in: int}. No user object.

I will review every line. Don't optimise for impressive — optimise
for boring and obvious.
```

## Example

Drop in your User model and the env-var loader for `JWT_SECRET`,
`JWT_ALG`, `JWT_EXPIRE_MINUTES`.

## Expected Output

`auth.py` should refuse to start with anything weaker than HS256 on a
32-byte secret. `decode_jwt` should call
`jwt.decode(token, secret, algorithms=[ALGORITHM])` (note the list)
and explicitly raise `InvalidAlgorithmError` if the token header
asks for `none`. The login endpoint should compute a dummy bcrypt
verify even when the user doesn't exist (constant-time, defeats
user enumeration).

## Common Pitfalls

- **`algorithms=ALGORITHM`** instead of `algorithms=[ALGORITHM]` —
  PyJWT silently lets *any* algorithm through if you pass a string.
  This is the classic JWT alg-confusion bug.
- **`algorithms=["HS256", "none"]`** — never include `none`.
- **Returning the user object on login.** Tempting; leaks PII into
  client-side storage. Return only the token.
- **Using SHA-256 to "hash" passwords.** Always bcrypt or argon2.
- **Loading `JWT_SECRET` with a default value.** Defaulting to a
  static string means an unconfigured prod is forgeable. Refuse to
  start.
- **Not checking `iss`/`aud` when you set them.** AI often mints with
  `iss="my-service"` then doesn't verify it on decode.

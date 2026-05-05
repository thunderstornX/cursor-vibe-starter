# 03 — Generate pytest tests from an implementation

## Context

Use this when you have a module of plain Python (`.py`) you've already
written and need a pytest suite that covers it before the diff goes up
for review. *Not* for TDD — for filling in coverage on existing code.

## Template

```
Generate pytest tests for the module below. Rules:
  - pytest function-style, no unittest.TestCase
  - Each test ends with a clear, single-responsibility assert
  - Cover (a) happy path, (b) every documented exception, (c) one
    boundary case per public function (empty input, oversized input,
    unicode, etc.)
  - Mock external I/O at the wire: respx for httpx, fakeredis for
    redis. NEVER monkeypatch the function under test.
  - Use the AAA structure (arrange / act / assert). Don't write the
    comments; the structure should be readable.

Module path: {path/to/module.py}

{paste module code here}
```

## Example

```
Module path: example/security-microservice/auth.py

{...code that hashes API keys with bcrypt and verifies JWTs...}
```

## Expected Output

```python
import pytest
from auth import hash_api_key, verify_api_key, mint_jwt, decode_jwt


def test_hash_api_key_roundtrips():
    key = "k_" + "a" * 32
    h = hash_api_key(key)
    assert verify_api_key(key, h) is True


def test_verify_api_key_rejects_wrong_key():
    h = hash_api_key("k_correct")
    assert verify_api_key("k_wrong", h) is False


def test_decode_jwt_rejects_none_alg():
    """attacker tries to bypass HMAC by setting alg=none"""
    bad_token = "..."
    with pytest.raises(InvalidTokenError):
        decode_jwt(bad_token)


def test_decode_jwt_rejects_expired():
    token = mint_jwt(sub="alice", expire_minutes=-1)
    with pytest.raises(ExpiredSignatureError):
        decode_jwt(token)
```

## Common Pitfalls

- **Tests that re-implement the function.** If a test recomputes the
  expected value with the same formula the function uses, it tests
  nothing. Pin a literal expected value when you can.
- **`assert thing.called`** without `assert_called_once_with(...)` is
  almost never enough. Verify the *arguments*, not just the call.
- **Mocking the function under test.** AI sometimes monkeypatches
  the very function the test is supposed to verify. Re-read who's
  mocking what.
- **Tests that share state via class attrs or module globals.** If
  test order matters, the test is wrong.

## Project overview
- This repository is a [monolith/service/library] built with [stack + versions].
- Main business domains: [billing, auth, learner-progress, etc.].

## Architecture
- Controllers should not contain business logic.
- Business logic should be covered by unit tests.

## What to review for
- Flag correctness issues, regression risks, missing edge cases, and unsafe error handling.
- Flag security-sensitive changes in auth, secrets, tokens, permissions, serialization, and input validation.
- Flag missing tests when business logic changes.
- Flag performance issues for loops over large collections, N+1 access patterns, blocking I/O, or repeated network/database calls.
- Flag observability gaps for new async/background flows.

## Testing and validation
- Suggest tests when code paths change without test coverage.
- Prefer existing fixtures/helpers in `tests/helpers/**`.
- If changing API contracts, ensure contract/integration tests are updated.

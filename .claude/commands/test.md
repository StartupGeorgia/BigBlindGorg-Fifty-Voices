---
name: test
description: Run all tests, fix failures with parallel agents
---

# Test Command

## Step 1: Run All Tests

### Backend (pytest):
```bash
cd backend && uv run pytest
```

### Frontend (vitest):
```bash
cd frontend && npm test
```

## Step 2: Options

### Watch Mode:
- Backend: `cd backend && uv run pytest --watch` (requires pytest-watch)
- Frontend: `cd frontend && npm run test:watch`

### Coverage:
- Backend: `cd backend && uv run pytest --cov=app --cov-report=html`
- Frontend: `cd frontend && npm run test:coverage`

### Filter Tests:
- Backend: `cd backend && uv run pytest -k "test_name"`
- Frontend: `cd frontend && npm test -- --filter="test name"`

### Run Only Backend:
```bash
cd backend && uv run pytest
```

### Run Only Frontend:
```bash
cd frontend && npm test
```

## Step 3: Fix Failures

If tests fail, spawn parallel agents using the Task tool:

1. **backend-test-fixer**: Fix failing Python tests
2. **frontend-test-fixer**: Fix failing TypeScript tests

Each agent should:
1. Read the failing test output
2. Identify the root cause
3. Fix the code or test
4. Re-run to verify

## Success Criteria

- All backend tests pass
- All frontend tests pass
- Coverage thresholds met (if configured)

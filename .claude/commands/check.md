---
name: check
description: Run all linting and typechecking, fix all issues
---

# Code Quality Check & Fix

Runs comprehensive quality checks on both backend and frontend, then fixes all issues.

## Detected Configuration

**Backend (Python):**
- Package Manager: uv
- Linter: ruff (40+ rule sets)
- Type Checker: mypy (strict mode)
- Formatter: ruff format
- Test Runner: pytest

**Frontend (TypeScript/Next.js):**
- Package Manager: npm
- Linter: ESLint (Next.js + TypeScript rules)
- Type Checker: TypeScript (strict mode)
- Formatter: Prettier
- Combined Check: `npm run check`

## Step 1: Run All Quality Checks

### Backend:
```bash
cd backend
echo "Running ruff linter..."
uv run ruff check app tests

echo "Running mypy type checker..."
uv run mypy app

echo "Checking code formatting..."
uv run ruff format --check app tests
```

### Frontend:
```bash
cd frontend
echo "Running comprehensive checks..."
npm run check
```

This runs: eslint + tsc + prettier check

## Step 2: Collect All Errors

Parse the output and group errors by type:
- **Type errors** (mypy, tsc)
- **Lint errors** (ruff, eslint)
- **Format errors** (ruff format, prettier)

## Step 3: Auto-Fix What's Possible

### Backend:
```bash
cd backend
# Auto-fix linting issues
uv run ruff check app tests --fix

# Auto-format code
uv run ruff format app tests
```

### Frontend:
```bash
cd frontend
# Auto-fix linting
npm run lint:fix

# Auto-format code
npm run format
```

## Step 4: Re-run Checks

Verify all auto-fixes worked:

### Backend:
```bash
cd backend
uv run ruff check app tests
uv run mypy app
uv run ruff format --check app tests
```

### Frontend:
```bash
cd frontend
npm run check
```

## Step 5: Manual Fix Remaining Issues

If any errors remain after auto-fix:
1. Read each error carefully
2. Fix the code
3. Re-run checks
4. Repeat until ZERO errors

## Step 6: Run Tests

Ensure nothing broke:

### Backend:
```bash
cd backend
uv run pytest
```

### Frontend:
```bash
cd frontend
npm test
```

## Step 7: Verify Clean State

Final verification:

```bash
# Backend
cd backend && uv run ruff check app && uv run mypy app && echo "✅ Backend clean"

# Frontend
cd frontend && npm run check && echo "✅ Frontend clean"
```

## Success Criteria

- ✅ Zero linting errors (backend + frontend)
- ✅ Zero type errors (backend + frontend)
- ✅ All code properly formatted
- ✅ All tests passing
- ✅ No warnings in output

**Do not complete until ALL criteria are met!**

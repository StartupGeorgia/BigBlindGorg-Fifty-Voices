---
name: check
description: Run all linting and typechecking, fix all issues
---

# Code Quality Check & Fix

Runs comprehensive quality checks on both backend and frontend, then fixes all issues.

## Project Configuration

**Backend (Python/FastAPI):**
- Package Manager: uv
- Linter: ruff (40+ rule sets)
- Type Checker: mypy (strict mode)
- Formatter: ruff format

**Frontend (TypeScript/Next.js):**
- Package Manager: npm
- Linter: ESLint (--max-warnings=0)
- Type Checker: TypeScript (tsc --noEmit)
- Formatter: Prettier

## Step 1: Run All Quality Checks

Run these commands and capture output:

```bash
# Backend checks
cd backend && uv run ruff check app tests 2>&1 || true
cd backend && uv run mypy app 2>&1 || true
cd backend && uv run ruff format --check app tests 2>&1 || true

# Frontend checks
cd frontend && npm run lint 2>&1 || true
cd frontend && npm run type-check 2>&1 || true
cd frontend && npm run format:check 2>&1 || true
```

## Step 2: Parse and Group Errors

Group errors by domain:
- **Backend type errors**: mypy issues
- **Backend lint errors**: ruff check issues
- **Backend format errors**: ruff format --check issues
- **Frontend type errors**: tsc issues
- **Frontend lint errors**: eslint issues
- **Frontend format errors**: prettier issues

## Step 3: Spawn Parallel Agents to Fix Issues

**IMPORTANT**: Use a SINGLE response with MULTIPLE Task tool calls to run agents in parallel.

For each domain with errors, spawn an agent:

1. **backend-fixer** agent: Fix all backend issues
   - Run `cd backend && uv run ruff check app tests --fix` for auto-fixable lint
   - Run `cd backend && uv run ruff format app tests` for formatting
   - Manually fix remaining mypy type errors
   - Verify with `cd backend && uv run ruff check app tests && uv run mypy app`

2. **frontend-fixer** agent: Fix all frontend issues
   - Run `cd frontend && npm run lint:fix` for auto-fixable lint
   - Run `cd frontend && npm run format` for formatting
   - Manually fix remaining TypeScript errors
   - Verify with `cd frontend && npm run check`

## Step 4: Verify All Fixes

After agents complete, run full verification:

```bash
# Backend
cd backend && uv run ruff check app tests && uv run mypy app && uv run ruff format --check app tests

# Frontend
cd frontend && npm run check
```

## Success Criteria

- Zero linting errors (backend + frontend)
- Zero type errors (backend + frontend)
- All code properly formatted
- No warnings in output

**Do not complete until ALL criteria are met!**

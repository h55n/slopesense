# Contributing to SlopeSense

Thank you for your interest in contributing to SlopeSense! This platform provides life-saving landslide risk intelligence to district officers and village leaders across India. We take quality seriously, and we welcome contributions that improve reliability, accuracy, and accessibility.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Development Environment](#2-development-environment)
3. [Project Structure](#3-project-structure)
4. [Development Standards](#4-development-standards)
5. [Testing Requirements](#5-testing-requirements)
6. [Branching and Commit Strategy](#6-branching-and-commit-strategy)
7. [Pull Request Process](#7-pull-request-process)
8. [Code of Conduct](#8-code-of-conduct)

---

## 1. Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/slopesense.git
   cd slopesense
   ```
3. **Set up** the development environment (see Section 2).
4. **Create** a feature branch (see Section 6).
5. **Submit** a Pull Request against the `main` branch.

---

## 2. Development Environment

### Backend (Python / FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start dev database + redis
docker-compose up -d db redis

# Run migrations
alembic upgrade head

# Start API with hot-reload
uvicorn backend.api.main:app --reload
```

### Frontend (Next.js / TypeScript)

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Environment Variables

```bash
cp .env.example .env
# Fill in NASA Earthdata credentials, Copernicus credentials, WhatsApp token
```

---

## 3. Project Structure

See the full structure in [`README.md`](README.md#repository-structure). Key directories:

| Directory | Language | Purpose |
|-----------|----------|---------|
| `backend/api/` | Python | FastAPI routes, middleware, cache |
| `backend/model/` | Python | FPI engine (core science) |
| `backend/ingestion/` | Python | Satellite data fetchers |
| `backend/alert/` | Python | Alert generation and dispatch |
| `backend/tests/` | Python | Pytest test suite |
| `frontend/src/` | TypeScript | Next.js dashboard |

---

## 4. Development Standards

### Python (Backend)

- **Python version**: 3.11+
- **Type hints**: All functions must have full type annotations (use `mypy` to check)
- **Formatting**: Run `black .` and `isort .` before committing
- **Linting**: `ruff check .` for additional lint rules
- **Docstrings**: All public modules, classes, and functions require Google-style docstrings
- **No `print()` statements**: Use `logging.getLogger(__name__)` throughout

```python
# Good
async def get_active_alerts(
    db: AsyncSession,
    min_fpi: float = 0.40,
    state: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch currently active alerts from the database.

    Args:
        db: Async SQLAlchemy session.
        min_fpi: Minimum FPI score filter (0.0–1.0).
        state: Optional ISO state code filter (e.g., "KL" for Kerala).

    Returns:
        List of alert dictionaries with all properties.
    """
    ...
```

### TypeScript (Frontend)

- **TypeScript strict mode**: No `any` types (use `unknown` or proper interfaces)
- **Component naming**: PascalCase for components, camelCase for utilities
- **Formatting**: `prettier` + `eslint` (run `npm run lint`)
- **No `console.log`**: Use proper error boundaries and toast notifications
- **Accessibility**: All interactive elements must have ARIA labels

```typescript
// Good — explicit interface, no any
interface AlertCardProps {
  alert: ActiveAlert;
  onDismiss?: (alertId: string) => void;
}

export function AlertCard({ alert, onDismiss }: AlertCardProps) { ... }
```

---

## 5. Testing Requirements

### Backend

All new endpoints, model changes, or processing changes **require tests**. Minimum coverage: **80%** for any new module.

```bash
# Run full test suite
pytest backend/tests/ -v

# Run with coverage report
pytest backend/tests/ --cov=backend --cov-report=html

# Run a specific test file
pytest backend/tests/test_api.py -v

# Run a specific test
pytest backend/tests/test_fpi.py::TestFPIEngine::test_basic_fpi_range -v
```

**Test file structure** — place tests in `backend/tests/test_<module>.py`:

```python
@pytest.mark.asyncio
class TestMyNewEndpoint:
    async def test_returns_correct_schema(self):
        """Test that the endpoint returns the expected JSON schema."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/my-endpoint")
        assert resp.status_code == 200
        data = resp.json()
        assert "key" in data
```

### Frontend

```bash
# Type checking
npx tsc --noEmit

# Lint
npm run lint
```

---

## 6. Branching and Commit Strategy

### Branch Naming

```
feature/short-description     # New features
fix/short-description         # Bug fixes
docs/short-description        # Documentation only
refactor/short-description    # Refactoring (no behaviour change)
test/short-description        # Test additions
```

**Examples:**
```
feature/add-email-dispatch
fix/geojson-empty-response
docs/api-authentication-guide
```

### Commit Messages

Follow **Conventional Commits** format:

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

**Examples:**
```
feat(api): add block-level FPI endpoint with state filter
fix(model): correct soil moisture weight coefficient
docs(arch): add mermaid sequence diagram for data flow
test(alert): add coverage for suppression threshold logic
```

---

## 7. Pull Request Process

1. **Ensure all tests pass** locally before opening a PR:
   ```bash
   pytest backend/tests/ -v
   cd frontend && npm run lint
   ```

2. **Update documentation** if you changed:
   - API endpoints → update `docs/API.md`
   - Database schema → update `ARCHITECTURE.md` ER diagram
   - Environment variables → update `.env.example`

3. **Update `CHANGELOG.md`** under `[Unreleased]` with a human-readable summary of your change.

4. **Fill in the PR template** with:
   - What problem this solves
   - How to test the change
   - Any breaking changes or migration notes

5. **Request review** from at least one maintainer.

6. **Address feedback** and keep the PR up to date with `main`.

### PR Checklist

- [ ] Tests pass (`pytest backend/tests/`)
- [ ] TypeScript compiles (`npx tsc --noEmit`)
- [ ] Lint passes (`npm run lint`)
- [ ] Documentation updated
- [ ] `CHANGELOG.md` updated
- [ ] No hardcoded secrets or credentials
- [ ] No debug `print()` or `console.log` statements left in

---

## 8. Code of Conduct

SlopeSense is built to save lives. We hold all contributors to a high standard of respectful, collaborative, and mission-driven behaviour.

- **Be kind**: Critique code, not people.
- **Be inclusive**: Disaster risk affects everyone; our team should too.
- **Be honest**: Report bugs and limitations clearly — inaccuracies cost lives.
- **Be responsive**: If you open a PR, stay engaged with the review process.

Violations should be reported to the maintainers via GitHub Issues (private).

---

*For questions, open a [GitHub Discussion](https://github.com/slopesense/slopesense/discussions) or file an issue.*

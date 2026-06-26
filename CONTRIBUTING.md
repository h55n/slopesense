# Contributing to SlopeSense

Thank you for your interest in contributing to SlopeSense! This platform aims to provide life-saving landslide risk intelligence, and we welcome contributions from developers, data scientists, and disaster management experts.

## Getting Started

1. **Fork and Clone**: Fork the repository and clone it to your local machine.
2. **Setup**: Follow the Quickstart guide in the `README.md` to set up your local environment (Docker, Node.js, Python).
3. **Branching**: Create a feature branch from `master` (e.g., `feature/new-model-integration` or `fix/map-rendering`).

## Development Standards

### Backend (Python / FastAPI)
- We use Python 3.11+.
- Ensure all code is typed using standard Python type hints.
- Format code using `black` and `isort`.
- Write unit tests for all new endpoints or processing functions in the `backend/tests/` directory.

### Frontend (Next.js / React)
- We use Next.js 14 App Router, TypeScript, and Tailwind CSS.
- Ensure strict TypeScript typing (`any` is discouraged).
- Run `npm run lint` before committing.
- Components should be modular and placed in `src/components`.

### Pull Request Process
1. Ensure your code passes all CI checks (linting, tests).
2. Update the `CHANGELOG.md` with your changes if significant.
3. Submit a Pull Request with a clear description of the problem solved or feature added.
4. Request a review from maintainers.

## Code of Conduct
Please be respectful and collaborative in issues and PRs. Our goal is to build robust, life-saving software.

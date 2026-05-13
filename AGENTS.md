# AGENTS.md - Kiro Gateway Agent Work Map

## Quick Start
1. Read `docs/architecture/overview.md`
2. Check `docs/workflows/development.md`
3. Run `python tools/verify.py` to verify environment

## Project Overview
- **Name**: Kiro Gateway
- **Tech Stack**: Python 3.11 / FastAPI / Hypercorn
- **Pattern**: Gateway proxy, multi-provider API transformation
- **Core Domains**: Routing, Auth, RateLimit, ModelResolution, Converters

## Directory Structure
| Directory | Purpose | Constraints |
|-----------|---------|-------------|
| `kiro/` | Core gateway logic | No direct HTTP, expose through routes |
| `kiro/routes_*.py` | API routes | Only parse requests/serialize responses |
| `kiro/converters_*.py` | Protocol conversion | Stateless pure functions |
| `kiro/models_*.py` | Data models | Pydantic BaseModel |
| `kiro/resolvers/` | Model resolution | External config driven |
| `tests/` | Tests | Unit + Integration |
| `docs/` | Documentation | Sync with code |

## Layer Rules (Enforced)
```
Models → Config → Converters → Resolvers → Services → Routes
  ↑                                              ↑
  └────── Only forward dependencies ─────────────┘
```

## Commands
```bash
# Development
python start.py              # Local start
hypercorn main:app --reload  # Hot reload

# Testing
pytest tests/ -v             # Run all tests
pytest tests/ -k "test_name" # Run specific test

# Checking
ruff check .                 # Code lint
ruff format .                # Code format
mypy kiro/                   # Type check

# Agent Self-Check
python tools/verify.py       # Environment verify
curl http://localhost:8000/health  # Health check
make diagnose                # Auto diagnose
```

## Key Documentation
- [Architecture Overview](docs/architecture/overview.md)
- [API Design Guide](docs/design/api-guidelines.md)
- [Development Workflow](docs/workflows/development.md)
- [Deployment Guide](docs/workflows/deployment.md)
- [Troubleshooting](docs/troubleshooting/)

## When Issues Occur
1. Check `docs/troubleshooting/` for relevant module
2. Run `make diagnose` for auto diagnosis
3. Check latest logs
4. Review active plans in `.agent/plans/`

## Golden Principles
1. **Shared tools first**: Use `kiro/utils/`, no hand-rolled helpers
2. **Boundary validation**: All external input via Pydantic, no direct `dict['key']`
3. **Structured logging**: Use logger, no `print()`
4. **Config driven**: Model mapping via config, no hardcoding

## Agent Skills
- [Bug Fix](.agent/skills/bug-fix.md)
- [Feature Dev](.agent/skills/feature-dev.md)
- [Refactor](.agent/skills/refactor.md)

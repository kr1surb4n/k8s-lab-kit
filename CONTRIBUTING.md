# Contributing to k8s-lab-kit

Thank you for considering a contribution! This project is a learning kit — clarity and correctness matter more than velocity.

## Ground Rules

- **Conventional Commits** — every commit message follows `type(scope): subject`
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`
  - Scope: the component touched (e.g., `graph-rag`, `boilerplates`, `recovery`)
  - Example: `feat(graph-rag): add two-hop graph expansion`
- **Tests Must Pass** — `make test` (38/38) before every push
- **No Secrets** — never commit passwords, tokens, keys, or local paths
- **Small, Focused PRs** — one logical change per PR; link the spec/issue

## Development Workflow

```bash
# 1. Sync and branch
git checkout main && git pull
git checkout -b feat/my-change

# 2. Make changes, run tests
make test                    # repo-level (38 tests)
cd ai/patterns/graph-rag && .venv/bin/python -m unittest discover -s app/tests

# 3. Commit with conventional message
git add -A
git commit -m "feat(scope): description"

# 4. Push and open PR
git push origin feat/my-change
# Open PR on GitHub; fill template
```

## Code Standards

| Language | Linter/Formatter | Config |
|---|---|---|
| Python | `ruff` + `black` | `pyproject.toml` |
| YAML | `yamllint` | `.yamllint.yml` |
| Shell | `shellcheck` | — |
| Markdown | `markdownlint` | `.markdownlint.json` |
| K8s manifests | `kubeval` + `conftest` | `policies/` |

Run `make lint` (if defined) or the individual tools before committing.

## Adding a New Component

1. **Check `specs/`** — is there a spec for this work?
2. **Follow the pattern** — look at `boilerplates/`, `ai/patterns/graph-rag/`
3. **Include** — README, tests, example doc (if user-facing), Makefile targets
4. **Update** — `docs/REPO-STATE.md`, `docs/coverage-matrix.md` if applicable

## Reporting Issues

- Use the GitHub issue templates (bug, feature, question)
- Include: `make test` output, `kubectl version`, minikube version, relevant logs
- For Graph RAG: include `eval/local-results.json` if evaluation-related

## Security

Report vulnerabilities via **GitHub Security Advisories** (private), not public issues.
See `SECURITY.md` for details.

## Questions?

Open a GitHub Discussion or issue with the `question` label.
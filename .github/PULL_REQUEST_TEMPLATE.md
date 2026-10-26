## Description

Brief summary of the change. Link the spec or issue.

Closes #<issue-number> (if applicable)

Related spec: `specs/<number>-<name>.md`

## Type of Change

- [ ] Bug fix (`fix`)
- [ ] New feature (`feat`)
- [ ] Documentation (`docs`)
- [ ] Refactor (`refactor`)
- [ ] Test (`test`)
- [ ] Chore (`chore`) — deps, build, CI, etc.
- [ ] Style (`style`) — formatting, no logic change

## Component(s) Affected

- [ ] Graph RAG app (`ai/patterns/graph-rag/app/`)
- [ ] Graph RAG eval (`ai/patterns/graph-rag/eval/`)
- [ ] Graph RAG k8s (`ai/patterns/graph-rag/k8s/`)
- [ ] Boilerplates (`boilerplates/`)
- [ ] Stacks (`boilerplates/stacks/`)
- [ ] Recovery (`recovery/`, `scripts/lab-drill.sh`)
- [ ] Observability (`observability/`)
- [ ] Docs / Guides (`docs/`, `guides/`)
- [ ] CI / Tooling (`.github/`, `Makefile`)
- [ ] Other: ___________

## Testing

- [ ] `make test` passes (38/38)
- [ ] Graph RAG unit tests pass (`cd ai/patterns/graph-rag && .venv/bin/python -m unittest discover -s app/tests`)
- [ ] `kubectl kustomize ai/patterns/graph-rag/k8s` renders without error
- [ ] `kubectl apply --dry-run=client -k ai/patterns/graph-rag/k8s` succeeds
- [ ] Manual verification steps (describe):

## Checklist

- [ ] Commit messages follow conventional commits (`type(scope): subject`)
- [ ] No secrets, tokens, keys, or local paths committed
- [ ] No generated artifacts (`.pyc`, `__pycache__`, `node_modules`, `*.log`, build outputs)
- [ ] Documentation updated (README, example doc, `docs/REPO-STATE.md` if component inventory changed)
- [ ] `docs/coverage-matrix.md` updated if new coverage
- [ ] CHANGELOG not needed (we use git log)

## Screenshots / Output (if applicable)

Paste relevant command output, dashboard screenshots, or diff highlights.

---

**Reviewer Guide**: Check tests, manifest validity, conventional commits, no secrets.
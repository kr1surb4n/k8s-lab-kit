# Analysis — `kubernetes_podsumowanie.md`

Status: analysis only. This file is the third source in the folder and the one the
PDF cites (citations 1 and 2, both pointing at it). Nothing here has been run.

---

## 1. What the file is

| Property | Value |
|---|---|
| Size | 1.7 KB, 20 lines, 4 sections |
| Language | Polish |
| Nature | A summary of "previously discussed topics" — an outline, not a lab |
| Code | none: zero commands, zero manifests, zero versions |
| Relationship to the PDF | It is the **source outline**: the PDF's four chapters are these four sections, in the same order, expanded |

The PDF's citation list names `kubernetes_podsumowanie.md` **and**
`kubernetes_podsumowanie.md.txt` as two separate works. They are the same
document, so the report cites its own input twice. That is a useful signal: the
PDF is generated from this outline, not written from experience.

---

## 2. What it actually says

Four sections, one idea each:

1. **Local environment and alternative distributions** — minikube is the main
   local environment; K3s and MicroK8s are lighter server-side alternatives for
   own-hardware and test deployments.
2. **Packages and deployments (Helm)** — Helm charts automate deployment,
   versioning and configuration of complex systems; the examples tried were
   Nginx and Magento.
3. **Configuration, network and data** — Services and Ingress expose apps
   outside the cluster; PV/PVC assign, map and persist disk; ConfigMap and
   environment variables configure applications.
4. **Learning and troubleshooting approach** — empirical troubleshooting of real
   errors and logs, no dry theory; build and run real projects instead of
   reading documentation passively.

There is no priority, no sequence, no acceptance criterion, and no environment
detail (no distro version, no RAM, no network).

---

## 3. What it adds to the two earlier sources

It changes nothing technically, but it settles three things:

- **The PDF is an expansion, not an independent source.** Every defect found in
  `01-analysis.md` §4 (invalid Deployment YAML, `SH_K3S_EXEC` instead of
  `INSTALL_K3S_EXEC`, `helm rollback ... 1`, the pinned Bitnami versions) lives in
  text the PDF *added*. The outline has no code, so it cannot be wrong — and it
  cannot be trusted as evidence either.
- **The author's stated method is "build it, then debug it".** That is exactly
  what this kit does (runbook → run → capture output → fix). Section 4 is the
  justification for the whole structure, and it is the only part of the outline
  that is a requirement rather than a topic list.
- **The examples were Nginx and Magento.** Nginx maps to exercises A1–A6. Magento
  never appears in the seven prompts; it is purely a Helm demonstration. So the
  Magento chart in the PDF is optional context, not lab work.

---

## 4. Coverage gap: the outline versus the actual exercise

This is the headline finding. The outline covers roughly **half** of what the
seven prompts demand.

| Outline bullet | Covered by A1–A7? | Where it lands |
|---|---|---|
| minikube | yes, it is the assumed runtime | A1–A7 |
| K3s / MicroK8s | only as a question | A4 ("would switching help?"), research R9 |
| Helm charts (Nginx) | no, the prompts never mention Helm | PDF lab H1 |
| Helm charts (Magento) | no | out of scope, optional |
| Services | yes | A1, A2, A6 |
| Ingress | no | PDF lab N1 only |
| PV / PVC | indirectly | A1 (hostPath, no PVC), A7 (SQLite file) |
| ConfigMap | yes | A2, A3 |
| Environment variables | yes | A3 |
| Empirical troubleshooting | implicit | T1 drills |

And the reverse gap — what the prompts require and the outline never mentions:

- access from another machine on the LAN (A4),
- Secrets (A5),
- three replicas, scaling, updates, rollback (A6),
- serving live files from the host disk (A1, A7),
- Laravel, PostgreSQL, SQLite (A7),
- readiness/liveness probes and rolling updates (A6).

**Conclusion:** the outline is a table of contents for the *theory*, while the
`.md` with the prompts is the *specification*. The PDF sits between them and
expands the theory but still ignores half the specification. Any plan built from
the PDF alone would finish with a reader who has never exposed a port to the LAN,
never used a Secret, and never scaled anything.

---

## 5. Consequences for the plan

1. **Keep the PDF as the theory index, not as the task list.** The runbooks stay
   driven by the seven `raw-content` blocks.
2. **Add a traceability artifact** so no outline bullet can be silently dropped:
   `docs/coverage-matrix.md`, one row per bullet, with the exercise, the artifact
   and the evidence that proves it. A bullet with no executable step is either
   moved to "out of scope" or deleted.
3. **Treat section 4 as an acceptance criterion, not a topic.** "Empirical, not
   dry" means every topic must end with a captured command output. That is why
   `docs/example-runs.md` exists and why the todo list asks for real transcripts.
4. **Magento stays optional.** It is the only item that needs a large chart with
   several dependencies; it is worth one isolated experiment, not a phase.
5. **The two citations being the same file** is a reminder to check claims rather
   than count references. Same rule as the PDF snippets: verify, then copy.

---

## 6. Defects in this file

- Section 2 says "Nginx and Magento" but never says which chart, which version,
  or whether it worked. Unfalsifiable.
- Section 3 lists "Services & Ingress" as one topic, which hides the fact that
  they operate at different layers (L4 vs L7) and have completely different
  failure modes.
- Section 3 says PV/PVC "assign, map and persist" data, but a hostPath mount —
  the thing both A1 and A7 actually need — involves neither PV nor PVC. The
  outline would send a reader down the wrong path.
- Section 4 is a preference ("avoid dry theory") presented without a method. The
  PDF later supplies the method (get → describe → logs → exec → port-forward), but
  the outline does not.
- No distro is fixed, so "minikube" and "K3s" are peers in the text while the PDF
  treats minikube as the default. That ambiguity is exactly what A4 asks about.

---

## 7. Definition of done for this source

- Every bullet in §2 has a row in `docs/coverage-matrix.md` with a status:
  `covered`, `partial`, `out of scope`.
- Every `covered` row names one command that proves it and one expected output.
- Every `out of scope` row names the reason.
- The matrix is re-checked at the end of the lab, so it reflects what was run,
  not what was planned.

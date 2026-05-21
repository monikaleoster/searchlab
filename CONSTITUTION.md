# SearchLab Constitution

> The non-negotiable principles that govern this project. Specs and code defer to this document. If a spec contradicts the constitution, the constitution wins and the spec must be amended.

**Version:** 1.0.1
**Ratified:** Phase 0 start
**Amendment process:** Any change requires bumping this file's version and adding an entry to the Amendments log at the bottom.

---

## I. Purpose

SearchLab exists for two reasons, in this order:

1. **Build hands-on search expertise that is publicly demonstrable.** Every phase must produce a LinkedIn-ready artifact (a measurement, a comparison, a live demo) before it is considered done.
2. **Ship a real enterprise search product** that an outside user could plausibly adopt.

When these goals conflict, **goal 1 wins through the lab phases**, and goal 2 begins to win once the retrieval research is done. This is a learning lab first and a product second, and the constitution exists to prevent feature creep from crowding out the learning loop.

---

## II. The Measurement Principle

**No retrieval change ships without a number.**

Phase 0 is the one exception — there is nothing to measure yet because there is no baseline and no golden set. From Phase 1 onward, every retrieval strategy, parameter change, and "small tweak" must be evaluated against the golden set and produce a row in the benchmark table. This is the single rule that separates this project from a tutorial.

Corollaries (effective Phase 1+):
- If a change is too small to bother evaluating, it is also too small to ship.
- If the golden set cannot detect a change, the golden set is the bug, not the change.
- Benchmark results are committed to the repo alongside the code that produced them. Numbers without reproducible code are rumors.

---

## III. The Loop-First Principle

The evaluation loop ships in **Phase 1**, before semantic retrieval, before the chat UI, before anything interesting. Phase 0's job is to build only the infrastructure that the loop will sit on top of.

Rationale: every later phase is a comparison against a baseline. Without the loop in place early, every subsequent phase has to retroactively justify itself, which never happens in practice.

---

## IV. One Phase, One Win, One Post

Each phase has **exactly one primary objective**. If a phase requires two objectives, it is two phases.

A phase is complete when:
1. The single objective is met.
2. (Phase 1+) The benchmark has been run and committed.
3. The LinkedIn post bullets exist as a file in the repo (`/posts/phase-N.md`).

A phase is **not** complete because the code works. The post is part of the deliverable.

---

## V. Boring Tech, Sharp Edges

The stack is deliberately conservative so that novelty stays in the retrieval layer, where the learning lives.

- **Language:** Java 21. Virtual threads where I/O concurrency matters.
- **Framework:** Spring Boot for HTTP and DI when needed. No reactive stack. No exotic frameworks.
- **Search:** OpenSearch via the `opensearch-java` client (never `RestHighLevelClient`).
- **Build:** Maven or Gradle, picked once in Phase 0 and never revisited.
- **Persistence:** OpenSearch is the only datastore until a phase explicitly justifies another.
- **Frontend:** Server-rendered (Thymeleaf + htmx) until proven insufficient. No SPA scaffolding without a real reason.

Adding a dependency requires answering in the spec: *what does this replace, and what does it cost in build time, container size, and conceptual load?*

---

## VI. Reproducibility

Anyone (including future-me) must be able to clone the repo and reproduce any result in the LinkedIn posts.

Requirements:
- `docker compose up` brings up OpenSearch with the version pinned.
- Setup is documented end-to-end in the README. A stranger should reach a working query in under 10 minutes.
- (Phase 1+) A single command runs the eval harness end-to-end, and benchmark result files are tagged with the git commit they were produced from.

---

## VII. Specification Discipline

This project follows specification-driven development. The order is always:

0. **Prompt** — before any Claude session that produces code or decisions, the prompt is written to `prompts/history.md` and committed. A session without a recorded prompt did not happen.
1. **Spec** — what we are building and why, written before code.
2. **Plan** — how it will be built, including tech choices and test approach.
3. **Tasks** — discrete, completable units of work.
4. **Code** — implementation.
5. **Evaluation** — the numbers (Phase 1+).
6. **Post** — the LinkedIn bullets.

Specs may be revised, but revisions are tracked. A spec that has been implemented and later changes must record the change with a rationale.

Each phase has its own folder under `/specs/phase-N/` containing at minimum: `spec.md`, `plan.md`, `tasks.md`. Phase 1 onward also requires `eval-criteria.md`.

---

## VIII. Scope Discipline

The brainstorm document lists many features (HyDE, query classification, multi-tenancy, metadata filtering, etc.). These are **roadmap items, not current-phase work.** A feature does not enter a phase's spec unless it is required to meet that phase's single objective.

If a feature feels tempting mid-phase, it goes into `/backlog.md`, not into the current spec.

---

## IX. Public-by-Default

The repo is public from Phase 0. Code, specs, benchmark results, and posts all live in the same repo. The audience is the LinkedIn reader who wants to see how the sausage is made.

This means:
- No secrets in the repo. API keys via environment variables, documented in `.env.example`.
- Commit messages are written assuming a stranger will read them.
- README is kept current; an out-of-date README is a bug.

---

## X. Definition of Done (per phase)

A phase ships when **all** of the following are true:

- [ ] Spec, plan, and tasks documents exist and are checked in.
- [ ] Code implements the spec.
- [ ] (Phase 1+) Benchmark has been run and results committed.
- [ ] LinkedIn post bullets exist at `/posts/phase-N.md`.
- [ ] README updated with the new capability and how to run it.
- [ ] Demo path works on a fresh clone (verified by re-running setup).

No phase is "almost done." It is done or it is in progress.

---

## Amendments

| Version | Date | Change | Rationale |
|---------|------|--------|-----------|
| 1.0.0 | Phase 0 start | Initial ratification | Baseline |
| 1.0.1 | 2026-05-18 | Added prompt recording as step 0 in Section VII; prompts/history.md introduced | Reproducibility — a session without a recorded prompt did not happen |
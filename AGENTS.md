# Repository Guidelines

## Project Structure & Module Organization
This repository is currently a minimal scaffold with no committed source files. As code is added, keep the layout predictable:

- `src/` for application code and reusable modules
- `tests/` for automated tests that mirror `src/`
- `assets/` for static files such as audio samples, fixtures, or images
- `scripts/` for local utilities such as setup, lint, or release helpers

Example: place `src/tts/engine.ts` alongside `tests/tts/engine.test.ts`.

## Build, Test, and Development Commands
There is no build system configured yet. When introducing one, expose a small, standard command set and document it here.

- `npm install` or equivalent: install project dependencies
- `npm run dev`: start the local development workflow
- `npm test`: run the automated test suite
- `npm run lint`: check formatting and static analysis issues
- `npm run build`: produce a distributable build

Prefer one primary package manager and avoid duplicating lockfiles.

## Coding Style & Naming Conventions
Use consistent formatting from the start:

- Indent with 2 spaces for JSON, YAML, and JavaScript/TypeScript
- Use descriptive, lowercase directory names such as `src/audio` or `tests/integration`
- Use `camelCase` for variables/functions, `PascalCase` for classes/components, and `kebab-case` for filenames unless a framework requires otherwise

If you add formatters or linters, wire them into the commands above and run them before opening a PR.

## Testing Guidelines
Put unit tests in `tests/` or next to source files if the chosen framework expects co-location. Name tests after the behavior under test, for example `engine.test.ts` or `engine.spec.ts`.

Add tests for new features and bug fixes. Prefer fast, deterministic tests over network-dependent checks.

## Commit & Pull Request Guidelines
Git history is not available in this workspace, so adopt a clear convention now: short, imperative commit subjects such as `Add audio normalization helper`.

For pull requests:

- describe the change and its impact
- link the related issue when one exists
- include test evidence (`npm test`, screenshots, logs) for behavior changes
- keep PRs focused on one concern

## Security & Configuration Tips
Do not commit secrets, API keys, or generated credentials. Keep local overrides in ignored files such as `.env.local`, and provide safe defaults in tracked examples like `.env.example`.

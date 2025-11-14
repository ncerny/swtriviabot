## General Instructions

- You MUST always read `AGENTS.md` in the root command before doing anything else.
- Follow the project's constitutional principles as outlined in `.specify/memory/constitution.md`.
- Ensure all code changes are covered by appropriate automated tests.
- Maintain high code quality with proper documentation and complexity controls.
- Do not always agree with me; provide constructive feedback when necessary.
- Do not assume anything not explicitly stated in the provided context.
- Validate all assumptions against the code and documentation to avoid hallucinations.
- Ensure that all commands are run in non-interactive mode so that you can read the output.

## Code Handling

- Use clear and concise language in all comments and documentation.
- All commits MUST reference relevant issues or tasks.
- All commits MUST follow conventional commit syntax.
- All tasks MUST be committed as soon as possible after completion.

## Python Specific Instructions

- Virtual Environment MUST ALWAYS be used for dependency management.
- Activate the virtual environment before running any scripts or tests.
- Use `pip` to manage dependencies and ensure `requirements.txt` is updated accordingly.
- Follow PEP 8 style guidelines for all Python code.

## Active Technologies

- Python 3.13+ (existing project standard) + GitHub Actions (workflow automation), pytest 8.4.2+ with pytest-cov 7.0.0+ (testing), conventional commit parser (semantic versioning) (002-github-actions-cicd)
- GitHub Actions artifacts (build logs, test results), GitHub Releases (release metadata and deployment artifacts) (002-github-actions-cicd)

- Python 3.13+ + discord.py 2.3+, python-dotenv, pytest 7.4+, pytest-asyncio 0.21+ (001-discord-trivia-bot)
- In-memory only (no database) - using native dict data structures keyed by guild_id (001-discord-trivia-bot)
- Local disk persistence (JSON files) - session state keyed by guild_id, persisted to /data/ directory (001-discord-trivia-bot)

## Recent Changes

- 002-github-actions-cicd: Added GitHub Actions CI/CD workflows (pr-tests.yml, release.yml, artifact.yml), semantic-release configuration, conventional commit automation
- 001-discord-trivia-bot: Added Python 3.13+ + discord.py 2.3+, python-dotenv, pytest 7.4+, pytest-asyncio 0.21+

# AGENTS.md - Household Project

## Project Overview
- Status: In Development (Phase 1).
- `household` is a desktop GUI household account book application.
- The app manages income, expenses, budgets, and assets as a replacement for spreadsheet-based management.
- Main entry point: `main.py`.
- UI modules live under `ui/`.
- Database schema, CRUD helpers, and report aggregation helpers live in `database.py`.

## Technology Stack
- Language: Python 3.10+
- GUI Framework: PyQt6
- Database: SQLite3
- Visualization: Matplotlib
- Excel Handling: openpyxl
- Packaging: PyInstaller

## Building And Running
- Install dependencies with `pip install -r requirements.txt`.
- If only following the minimal GEMINI.md setup, install PyQt6 with `pip install PyQt6`.
- Run the application with `python main.py`.
- For a quick syntax check, run `python -m py_compile main.py ui/*.py`.
- In this Codex environment, the bundled Python may be available at `C:\Users\rlatj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

## Development Conventions
- Keep UI definitions and behavior separate from business logic where practical.
- Prefer placing UI behavior in the relevant `ui/*_tab.py` file.
- Keep database access centralized in `database.py`; avoid ad hoc SQL in UI modules unless following an existing local pattern.
- Use the existing PyQt6 widget and stylesheet patterns before adding new abstractions.
- Follow PEP 8 naming for Python code where it does not conflict with nearby style.
- Refer to `PLAN.md` for the broader development roadmap.
- Preserve Korean UI text and existing emoji labels unless the task asks to change them.

## UI Notes
- Global app styles are defined in `main.py` as `COMMON_STYLE`, `LIGHT_STYLE`, and `DARK_STYLE`.
- Theme-aware widgets should rely on the global stylesheet where possible.
- If code must branch by theme, follow the existing `QApplication.instance().styleSheet()` pattern.
- Report charts are centralized in `ui/report_tab.py`; keep chart font sizes consistent through the existing chart constants.

## Data And Generated Files
- Do not commit local runtime database files such as `household.db` unless explicitly requested.
- Do not commit generated Python cache directories such as `__pycache__/`.
- Do not commit PyInstaller output, temporary files, or local virtual environments.

## Git Commit Convention
- Commit messages should use the following conventional prefix format.
- Write the detailed commit message content in Korean.
- `feat`: new feature
- `fix`: bug fix or syntax/runtime error fix
- `bug`: work related to a reported known bug
- `docs`: documentation updates such as `GEMINI.md`, `PLAN.md`, or `AGENTS.md`
- `style`: formatting or UI/layout styling without core logic changes
- `refactor`: code restructuring without behavior changes

## Version And Release Rules
- Do not create Git tags unless the user explicitly asks to create a tag.
- Do not infer version numbers or create releases without a direct user request.
- Do not push until the user asks for push or confirms prepared commits.
- When pushing a tag, summarize the commit history since the previous tag and use that summary as the tag message.
- When a release is created from a pushed tag, write release notes in Korean using grouped sections. Use categories such as `🐛 버그 수정`, `✨ 기능 추가`, `🎨 디자인 수정`, `📝 문서 수정`, `♻️ 리팩토링`, and `🔧 기타 변경`; omit empty categories.
- Under each release note category, list concrete changes as nested bullet items.
- Release note format:
  - `## 🐛 버그 수정`
    - `- 수정된 문제 요약`
  - `## ✨ 기능 추가`
    - `- 추가된 기능 요약`
  - `## 🎨 디자인 수정`
    - `- 변경된 화면/스타일 요약`
  - `## 📝 문서 수정`
    - `- 변경된 문서 요약`
  - `## ♻️ 리팩토링`
    - `- 개선된 코드 구조 요약`
  - `## 🔧 기타 변경`
    - `- 그 외 변경사항 요약`

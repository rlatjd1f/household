# GEMINI.md - Household Project

## Project Overview
**Status:** In Development (Phase 1)

The `household` project is a desktop GUI household account book application. It aims to provide a convenient way to manage income, expenses, budgets, and assets, replacing traditional spreadsheet-based management.

## Technology Stack
- **Language:** Python 3.10+
- **GUI Framework:** PyQt6
- **Database:** SQLite3

## Building and Running
- **Install Dependencies:** `pip install PyQt6`
- **Run Application:** `python main.py`

## Development Conventions
- **UI/Logic Separation:** Keep UI definitions (or Qt Designer files) separate from business logic.
- **Database:** Use a single `database.db` file for local storage.
- **Naming:** Follow PEP 8 for Python code.
- **Documentation:** Refer to `PLAN.md` for the detailed development roadmap.

### Git Commit Convention
커밋 메시지는 다음의 형식을 따르며, 상세 내용은 **한국어**로 작성합니다.
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정 또는 문법 오류 해결
- `bug`: 알려진 버그 리포트 관련 작업
- `docs`: 문서 수정 (GEMINI.md, PLAN.md 등)
- `style`: 코드 포맷팅, 세미콜론 누락 등 (로직 변경 없음)
- `refactor`: 코드 리팩토링

# Skill: Secure Checkpoint
**Trigger:** When the user says 'checkpoint your work', 'run secure checkpoint', or at the end of a major phase.

**Execution Steps:**
1. **Secret Scan:** Run `git status`. Ensure no `.env` or sensitive key files are staged. If they are, run `git reset HEAD <file>` and add them to `.gitignore`.
2. **Verification:** 
   - `cd apps/web && npm run lint` (Auto-fix if possible).
   - `cd ../api && pytest && mypy .` 
   - **HALT** if any tests fail. Do not commit.
3. **Commit:**
   - `git add .`
   - `git commit -m "<type>: <description>"` using Conventional Commits (feat, fix, chore, refactor, docs).
4. **Output:** Print the commit hash and message to the terminal.

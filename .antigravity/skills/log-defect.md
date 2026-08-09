# Skill: Log Defect
**Trigger:** When told to "log a defect", or automatically after fixing a bug (especially if a test fails during a checkpoint).

**Execution Steps:**
1. Open `docs/DEFECT_LEDGER.md`.
2. Append a new entry at the bottom using this exact format:
   ## [BUG-XXX] - Date: YYYY-MM-DD
   * **Issue:** (Brief description of the failure or bug)
   * **Root Cause:** (Technical explanation of *why* it happened)
   * **Resolution:** (How it was fixed)
   * **Files Touched:** (List of files updated)
3. Save the file.
4. Output a confirmation to the user with the Defect-ID.

# Specification: Open Telemetry in a Separate Page

## 1. Goal Description
Clicking on the "Telemetry Flow" option under the "Dev Tools" dropdown menu in the application header currently navigates the active page to the telemetry viewer page (e.g., `/[lang]/dev/telemetry`). This causes the user to lose their current application context/state. The goal is to change this behavior so that clicking "Telemetry Flow" opens the telemetry flow viewer in a separate browser tab or window, leaving the main application page and its active session/context completely unaffected.

---

## 2. Functional Requirements
- **Target Link Option**: The "Telemetry Flow" item in the Dev Tools dropdown menu must open the telemetry route (`/[lang]/dev/telemetry`) in a new browser tab or window.
- **Link Implementation**: Use an appropriate HTML anchor element (`<a>` or Next.js `<Link>`) with standard attributes `target="_blank"` and `rel="noopener noreferrer"`.
- **Close Dropdown**: Clicking the link should close the developer space dropdown.
- **Preserve Application State**: The current application view, input fields, active dialogue state, or other user actions must remain intact without reloading or navigating away.

---

## 3. Non-Functional Requirements & Guardrails
- **UX & Clicks**: Standard link behavior should be maintained (e.g., middle-clicking or Cmd/Ctrl-clicking should also work as expected).
- **Styling Consistency**: The menu option's visual appearance, hover states, and padding must remain exactly identical to the other dropdown options.

---

## 4. Acceptance Criteria
1. Clicking "Telemetry Flow" under the "Dev Tools" dropdown opens the `/[lang]/dev/telemetry` path in a new browser tab.
2. The original tab/window containing the application remains on the same page with all state/inputs preserved.
3. The visual appearance of the "Telemetry Flow" option matches the other Dev Tools options perfectly.
4. No console errors or UI layout regressions are introduced.

---

## 5. Verification Plan
- **Manual Verification**:
  1. Open the application and navigate to a project detail view.
  2. Input some text in the Dialogue Panel or perform an interaction to establish active context.
  3. Click "Dev Tools" -> "Telemetry Flow".
  4. Verify that a new browser tab/window opens showing the Telemetry Flow Viewer.
  5. Verify that the original tab remains on the project detail view with the dialog panel and other state completely untouched.

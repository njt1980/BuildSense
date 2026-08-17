# System Design: Open Telemetry in a Separate Page

## 1. Architecture & UI Changes

We will modify the Dev Tools dropdown menu inside the `GlobalHeader` component.

```text
User clicks 'Dev Tools' -> Dropdown opens
  -> Click 'Telemetry Flow'
       - Opens '/[lang]/dev/telemetry' in a new browser tab/window
       - Closes the dropdown menu
       - Leaves current page state unaffected
```

The component responsible is `apps/web/src/components/global-header.tsx`.

---

## 2. Component Design & Changes

### 2.1 Modify `global-header.tsx`

We will change the "Telemetry Flow" `<button>` element to an HTML `<a>` anchor element with the following attributes:
- `href={`/${lang}/dev/telemetry`}`
- `target="_blank"`
- `rel="noopener noreferrer"`
- `onClick={() => setDevDropdownOpen(false)}`

We will also update the CSS classes:
- Replace `w-full` with `block w-full` to ensure the `<a>` element behaves like a block element, filling the width of the dropdown and keeping styling consistent.

No other components or styles will be affected.

---

## 3. Atomic Implementation Steps

### Step 1: Update Telemetry Flow Option
- **Read file**: [`global-header.tsx`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/web/src/components/global-header.tsx)
- **Modify file**: [`global-header.tsx`](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/web/src/components/global-header.tsx)
- **Action**: Change "Telemetry Flow" button to an anchor tag with `target="_blank"` and `rel="noopener noreferrer"`.

---

## 4. Verification & Testing Design

### 4.1 Automated Validation
Run linting and TypeScript checks:
- Directory: `apps/web`
- Commands:
  - `npm run type-check`
  - `npm run lint`

### 4.2 Manual Dry Run
- Open the application.
- Navigate to the Dev Tools menu.
- Verify clicking "Telemetry Flow" opens the telemetry view in a new tab.
- Verify the active workspace / application page stays open and interactive.

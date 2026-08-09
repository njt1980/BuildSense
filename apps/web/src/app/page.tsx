import * as React from "react";
import { DualViewLayout } from "@/components/dual-view-layout";

/**
 * Root landing page of the BuildSense application.
 * Renders the primary Dual-View layout containing suggester, evaluator, and optimizer states.
 *
 * @returns React node representing the application root dashboard.
 */
export default function Home(): React.JSX.Element {
  return (
    <DualViewLayout />
  );
}

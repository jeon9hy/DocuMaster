import { AppShell } from "@/components/layout/AppShell";
import { WorkspaceProvider } from "@/state/WorkspaceProvider";

export default function Home() {
  return (
    <WorkspaceProvider>
      <AppShell />
    </WorkspaceProvider>
  );
}

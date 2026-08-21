import { Header } from "@/components/layout/header";
import { ProtectedPage } from "@/components/layout/protected-page";

export function AppShell({ children }: { children: React.ReactNode }) {
  return <ProtectedPage><Header/>{children}</ProtectedPage>;
}

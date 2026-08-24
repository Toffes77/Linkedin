import { Header } from "@/components/layout/header";
import { ProtectedPage } from "@/components/layout/protected-page";
import { MessagesDock } from "@/components/messages/messages-dock";

export function AppShell({ children }: { children: React.ReactNode }) {
  return <ProtectedPage><Header/>{children}<MessagesDock/></ProtectedPage>;
}

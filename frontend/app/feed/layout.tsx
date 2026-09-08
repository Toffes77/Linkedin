import { Suspense } from "react";
import { SessionLoader } from "@/components/session-loader";

export default function FeedLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<SessionLoader />}>{children}</Suspense>;
}

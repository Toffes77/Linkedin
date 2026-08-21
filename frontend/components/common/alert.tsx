export function Alert({ children, success = false }: { children: React.ReactNode; success?: boolean }) {
  return <div role={success ? "status" : "alert"} className={`notice ${success ? "notice-success" : "notice-error"}`}>{children}</div>;
}

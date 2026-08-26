export function SessionLoader() {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 text-slate-600">
      <div className="flex items-center gap-3" role="status">
        <span className="session-spinner" />
        Comprobando sesión...
      </div>
    </main>
  );
}

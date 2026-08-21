export function SessionLoader() {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 text-slate-600">
      <div className="flex items-center gap-3" role="status">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        Comprobando sesión...
      </div>
    </main>
  );
}

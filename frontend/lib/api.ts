export const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL no está configurada");
}

export type Experience = { id: number; empresa_id: number; puesto: string; desde: string; hasta: string | null };
export type User = { id: number; nombre: string; headline: string; ciudad: string; foto_perfil_url: string | null; experiencias: Experience[] };
export type Company = { id: number; nombre: string; industria: string | null; sitio_web: string | null; foto_perfil_url: string | null };
export type CompanyRole = "OWNER" | "RECRUITER";
export type CompanyMember = { empresa_id: number; usuario_id: number; rol: CompanyRole };
export type Connection = { usuario_a: number; usuario_b: number; fecha: string; estado: "pendiente" | "aceptada" | "rechazada" };
export type Post = { id: number; autor_id: number; texto: string; fecha: string };
export type ReactionType = "like" | "celebrar" | "apoyar" | "interesante";
export type Reaction = { usuario_id: number; publicacion_id: number; tipo: ReactionType };
export type ReactionCounts = Record<ReactionType, number>;
export type Job = { id: number; empresa_id: number; titulo: string; descripcion: string; publicada: boolean; fecha_publicacion: string | null };
export type ApplicationStatus = "nueva" | "vista" | "entrevista" | "contratado" | "rechazada";
export type Application = { id: number; oferta_id: number; usuario_id: number; fecha: string; estado: ApplicationStatus };
export type JobStats = { oferta_id: number; total_postulaciones: number; postulaciones_por_estado: Record<ApplicationStatus, number>; dias_desde_publicacion: number | null };

type ApiOptions = Omit<RequestInit, "credentials"> & { json?: unknown };
type ValidationIssue = { loc?: Array<string | number>; msg?: string };

export class ApiError extends Error {
  constructor(public readonly status: number, message: string, public readonly details?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(body: unknown, status: number) {
  if (body && typeof body === "object") {
    if ("message" in body && typeof body.message === "string") return body.message;
    if ("detail" in body) {
      if (typeof body.detail === "string") return body.detail;
      if (Array.isArray(body.detail)) {
        return (body.detail as ValidationIssue[]).map((item) => {
          const field = item.loc?.filter((part) => part !== "body").join(".");
          return `${field ? `${field}: ` : ""}${item.msg ?? "Dato inválido"}`;
        }).join(" · ");
      }
    }
  }
  return status >= 500 ? "Ocurrió un error en el servidor." : "No se pudo completar la solicitud.";
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { json, headers, ...requestOptions } = options;
  const response = await fetch(`${API_URL}${path}`, {
    ...requestOptions,
    body: json === undefined ? options.body : JSON.stringify(json),
    credentials: "include",
    headers: { ...(json === undefined ? {} : { "Content-Type": "application/json" }), ...headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (response.status === 401 && typeof window !== "undefined") window.dispatchEvent(new Event("auth:unauthorized"));
    throw new ApiError(response.status, errorMessage(body, response.status), body);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function mediaUrl(path: string | null | undefined) {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

export const authApi = {
  me: () => apiFetch<User>("/api/usuarios/me"),
  login: (email: string, password: string) => apiFetch<{ access_token: string; token_type: string }>("/api/auth/login", { method: "POST", json: { email, password } }),
  logout: () => apiFetch<{ message: string }>("/api/auth/logout", { method: "POST" }),
};

export const usersApi = {
  create: (data: { email: string; password: string; nombre: string; headline: string; ciudad: string }) => apiFetch<User>("/api/usuarios", { method: "POST", json: data }),
  get: (id: number) => apiFetch<User>(`/api/usuarios/${id}`),
  search: (q: string, ciudad?: string) => apiFetch<User[]>(`/api/buscar/usuarios?${new URLSearchParams({ q, ...(ciudad ? { ciudad } : {}) })}`),
  suggestions: (id: number) => apiFetch<User[]>(`/api/usuarios/${id}/sugerencias`),
  update: (data: { nombre?: string; headline?: string; ciudad?: string }) => apiFetch<User>("/api/usuarios/me", { method: "PUT", json: data }),
  password: (password_actual: string, password_nueva: string) => apiFetch<{ message: string }>("/api/usuarios/me/password", { method: "PUT", json: { password_actual, password_nueva } }),
  photo: (foto: File) => { const body = new FormData(); body.append("foto", foto); return apiFetch<User>("/api/usuarios/me/foto-perfil", { method: "PUT", body }); },
  addExperience: (userId: number, data: { empresa_id: number; puesto: string; desde: string; hasta: string | null }) => apiFetch<Experience>(`/api/usuarios/${userId}/experiencias`, { method: "POST", json: data }),
};

export const connectionsApi = {
  create: (from: number, to: number) => apiFetch<Connection>("/api/conexiones", { method: "POST", json: { usuario_a: from, usuario_b: to } }),
  respond: (from: number, to: number, estado: "aceptada" | "rechazada") => apiFetch<Connection>(`/api/conexiones/${from}/${to}`, { method: "PATCH", json: { estado } }),
};

export const postsApi = {
  feed: (userId: number, page = 1) => apiFetch<Post[]>(`/api/usuarios/${userId}/feed?page=${page}`),
  create: (texto: string) => apiFetch<Post>("/api/publicaciones", { method: "POST", json: { texto } }),
  update: (id: number, texto: string) => apiFetch<Post>(`/api/publicaciones/${id}`, { method: "PUT", json: { texto } }),
  delete: (id: number) => apiFetch<void>(`/api/publicaciones/${id}`, { method: "DELETE" }),
  reactionCounts: (id: number) => apiFetch<ReactionCounts>(`/api/publicaciones/${id}/reacciones`),
  react: (userId: number, postId: number, tipo: ReactionType) => apiFetch<Reaction>("/api/reacciones", { method: "POST", json: { usuario_id: userId, publicacion_id: postId, tipo } }),
  changeReaction: (postId: number, tipo: ReactionType) => apiFetch<Reaction>(`/api/publicaciones/${postId}/reacciones`, { method: "PATCH", json: { tipo } }),
};

export const companiesApi = {
  get: (id: number) => apiFetch<Company>(`/api/empresas/${id}`),
  create: (data: { nombre: string; industria: string | null; sitio_web: string | null }) => apiFetch<Company>("/api/empresas", { method: "POST", json: data }),
  update: (id: number, data: Partial<Pick<Company, "nombre" | "industria" | "sitio_web">>) => apiFetch<Company>(`/api/empresas/${id}`, { method: "PUT", json: data }),
  photo: (id: number, foto: File) => { const body = new FormData(); body.append("foto", foto); return apiFetch<Company>(`/api/empresas/${id}/foto-perfil`, { method: "PUT", body }); },
  members: (id: number) => apiFetch<CompanyMember[]>(`/api/empresas/${id}/usuarios`),
  addMember: (id: number, usuario_id: number, rol: CompanyRole) => apiFetch<CompanyMember>(`/api/empresas/${id}/usuarios`, { method: "POST", json: { usuario_id, rol } }),
  updateMember: (id: number, userId: number, rol: CompanyRole) => apiFetch<CompanyMember>(`/api/empresas/${id}/usuarios/${userId}`, { method: "PATCH", json: { rol } }),
  removeMember: (id: number, userId: number) => apiFetch<void>(`/api/empresas/${id}/usuarios/${userId}`, { method: "DELETE" }),
};

export const jobsApi = {
  published: () => apiFetch<Job[]>("/api/ofertas/publicadas"),
  get: (id: number) => apiFetch<Job>(`/api/ofertas/${id}`),
  byCompany: (id: number) => apiFetch<Job[]>(`/api/empresas/${id}/ofertas`),
  create: (data: { empresa_id: number; titulo: string; descripcion: string; publicada: boolean }) => apiFetch<Job>("/api/ofertas", { method: "POST", json: data }),
  update: (id: number, data: Partial<Pick<Job, "titulo" | "descripcion" | "publicada">>) => apiFetch<Job>(`/api/ofertas/${id}`, { method: "PUT", json: data }),
  stats: (id: number) => apiFetch<JobStats>(`/api/ofertas/${id}/estadisticas`),
  apply: (jobId: number, userId: number) => apiFetch<Application>("/api/postulaciones", { method: "POST", json: { oferta_id: jobId, usuario_id: userId } }),
  applicationsByUser: (userId: number) => apiFetch<Application[]>(`/api/usuarios/${userId}/postulaciones`),
  applicationsByJob: (jobId: number) => apiFetch<Application[]>(`/api/ofertas/${jobId}/postulaciones`),
  updateApplication: (id: number, estado: ApplicationStatus) => apiFetch<Application>(`/api/postulaciones/${id}`, { method: "PATCH", json: { estado } }),
};

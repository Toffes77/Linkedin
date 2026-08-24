<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Manual operativo del frontend

Este archivo aplica a todo `frontend/`. El README de la raíz explica instalación y funcionalidades; este documento define cómo modificar la interfaz sin romper sus patrones.

## Antes de editar

1. Ejecutar `git status` desde la raíz y conservar cualquier cambio existente.
2. Leer las guías locales de Next.js relevantes en `node_modules/next/dist/docs/` antes de escribir código.
3. Inspeccionar la página, los componentes, `lib/api.ts` y los estilos relacionados con el pedido.
4. Abrir todas las referencias visuales indicadas, normalmente bajo `../referencias_frontend/`.
5. Limitar los cambios al objetivo solicitado y usar `apply_patch` para editar archivos.

No revertir trabajo ajeno, no hacer rediseños generales y no modificar comportamiento no relacionado para simplificar una tarea local.

## Next.js, React y TypeScript

- El proyecto usa Next.js 16 App Router, React 19 y TypeScript.
- Las rutas viven en `app/`; la UI reutilizable vive en `components/` y el acceso REST en `lib/`.
- Los layouts y páginas son Server Components por defecto. Agregar `"use client"` únicamente cuando el componente necesite estado, efectos, eventos o APIs del navegador.
- No convertir árboles completos a Client Components si basta con aislar una pieza interactiva.
- Mantener tipos explícitos para contratos de API y estados relevantes. No usar `any` para evitar resolver un contrato real.
- Consultar la documentación incluida con la versión instalada; no asumir APIs de otra versión de Next.js.

## API y datos

Todas las peticiones REST deben centralizarse en `frontend/lib/api.ts`.

Usar y extender:

- `apiFetch`
- `authApi`
- `usersApi`
- `connectionsApi`
- `followsApi`
- `postsApi`
- `companiesApi`
- `jobsApi`
- `messagesApi`
- `notificationsApi`

No hacer fetch hardcodeado dentro de componentes, por ejemplo:

```ts
fetch("http://localhost:8000/api/...")
```

`apiFetch` debe seguir construyendo las URLs desde `NEXT_PUBLIC_API_URL` y enviando `credentials: "include"`. Añadir un método al módulo de dominio correspondiente cuando se necesite un endpoint nuevo.

## Autenticación

- Reutilizar `AuthProvider`, `useAuth`, `ProtectedPage` y `AppShell`.
- Mantener la sesión mediante cookie HttpOnly; el cliente no necesita ni debe intentar leer esa cookie.
- No mover el JWT a `localStorage`, `sessionStorage` ni estado persistente del navegador.
- No romper el soporte Bearer del backend ni el tratamiento global de respuestas `401`.
- Las páginas públicas de autenticación no deben incluir controles destinados a páginas protegidas.
- Ocultar controles sin permiso mejora la UX, pero nunca reemplaza la autorización del backend.

## Componentes y estado

- Reutilizar `Avatar`, `Header`, `AppShell`, loaders, alertas, cards y estados vacíos existentes.
- Evitar componentes gigantes; separar lista, fila, formulario o ventana cuando tengan estado y responsabilidades propias.
- No duplicar navegación, avatares, resolución de URLs de imágenes ni llamadas API.
- Preservar estados cargando, vacío y error siguiendo el patrón de la pantalla existente.
- Al agregar efectos asíncronos, contemplar desmontaje, intervalos, abortos y respuestas fuera de orden cuando corresponda.

## Estilos y referencias visuales

- Los estilos compartidos viven en `app/globals.css`.
- Mantener la estética tipo LinkedIn existente: superficies blancas, bordes discretos, tipografía sobria y colores actuales.
- Analizar dimensiones, espaciados, estados y responsive de las imágenes de referencia antes de implementar un diseño.
- No usar una captura como fondo ni copiar contenido rasterizado como interfaz.
- No agregar librerías UI, gradientes, glassmorphism, sombras exageradas o animaciones sin una necesidad explícita.
- Un pedido local no autoriza cambiar globalmente colores, tipografía, breakpoints o layout.
- Verificar ancho disponible, overflow y scroll interno en desktop y mobile.

## Empresas y roles

Distinguir siempre pertenencia de autorización:

- `OWNER`: edición de empresa/logo, miembros y las herramientas administrativas implementadas.
- `RECRUITER`: ofertas, postulaciones y estadísticas implementadas.
- `COLLABORATOR`: pertenencia sin permisos administrativos.

No ampliar condiciones como `OWNER || RECRUITER` para incluir `COLLABORATOR`. Una empresa debe aparecer en las empresas del colaborador, pero eso no habilita controles de administración.

## Mensajes privados

- Mensajes y Notificaciones son sistemas separados; no mezclar indicadores ni APIs.
- Los contactos provienen de conexiones aceptadas.
- Mantener una conversación por par y no enviar un `autor_id` desde la interfaz.
- Conservar el polling actual de 5 segundos salvo que el pedido requiera explícitamente otra estrategia.
- Mantener búsqueda por nombre, puntos verdes, lectura al abrir y orden por último mensaje.
- Minimizar no debe destruir historial, conversación seleccionada ni borrador.
- Cerrar una ventana solo modifica la UI; no elimina mensajes ni conversaciones.
- El scroll de contactos e historial debe permanecer dentro del panel mediante overflow natural y `overscroll-behavior`.

## Validación

Después de cualquier cambio frontend ejecutar desde `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
```

En Unix puede usarse `npm`. Para cambios visuales, comprobar también los estados relevantes y anchos responsive en un navegador cuando esté disponible.

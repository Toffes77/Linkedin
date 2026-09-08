# Frontend

Interfaz del clon simplificado de LinkedIn construida con Next.js 16 App Router, React 19 y TypeScript.

La documentación principal de instalación, configuración y funcionalidades está en [`../README.md`](../README.md). Las reglas operativas para agentes que modifiquen esta aplicación están en [`AGENTS.md`](AGENTS.md).

## Inicio rápido

Desde `frontend/`:

```bash
npm install
npm run dev
```

Crear `.env.local` desde `.env.example` y configurar `NEXT_PUBLIC_API_URL`. La aplicación queda disponible normalmente en <http://localhost:3000>.

La página pública `/terminos` renderiza `content/terminos.md`. El registro exige enviar `acepta_terminos: true` después de marcar ese enlace; la aceptación se valida y se descarta, sin guardarse en la base.

Las llamadas REST se centralizan en `lib/api.ts`; los componentes no deben hardcodear la URL del backend.

## Validación

```powershell
npm.cmd run lint
npm.cmd run build
```

En Unix puede utilizarse `npm` en lugar de `npm.cmd`.

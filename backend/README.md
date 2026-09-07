# Backend

API del clon simplificado de LinkedIn construida con FastAPI, SQLAlchemy, Pydantic y PostgreSQL.

La documentación principal de instalación, variables de entorno, base de datos y funcionalidades está en [`../README.md`](../README.md). Las reglas operativas para agentes que modifiquen esta aplicación están en [`AGENTS.md`](AGENTS.md).

## Inicio rápido

Desde `backend/`:

```bash
python -m venv .venv
pip install -r requirements.txt
```

Crear `.env` desde `.env.example`, inicializar PostgreSQL con `src/db/tables.sql` si se trata de una base nueva y ejecutar:

```bash
python -m src.main
```

Swagger queda disponible en <http://localhost:8000/docs>.

## Arquitectura

```text
Router → Service → Repository → PostgreSQL
```

Models SQLAlchemy, Schemas, DTOs y Mappers permanecen separados. Las queries deben vivir en Repository y las reglas de negocio/autorización en Service.

## Tests

```bash
python -m unittest discover -s tests -v
```

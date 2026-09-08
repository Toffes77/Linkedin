# Backend

API del clon simplificado de LinkedIn construida con FastAPI, SQLAlchemy, Pydantic y PostgreSQL.

La documentación principal de instalación, variables de entorno, base de datos y funcionalidades está en [`../README.md`](../README.md). La referencia completa de endpoints está en [`API.md`](API.md). Las reglas operativas para agentes que modifiquen esta aplicación están en [`AGENTS.md`](AGENTS.md).

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

Swagger queda disponible en [`http://localhost:8000/docs`](http://localhost:8000/docs); el esquema OpenAPI está en [`http://localhost:8000/openapi.json`](http://localhost:8000/openapi.json). Para la guía legible por dominio, consultar [`API.md`](API.md).

## Arquitectura

```text
Router → Service → Repository → PostgreSQL
```

Models SQLAlchemy, Schemas, DTOs y Mappers permanecen separados. Las queries deben vivir en Repository y las reglas de negocio/autorización en Service.

## Tests

```bash
python tests/run_isolated.py
```

Como protección adicional, `src.db.connection` detecta procesos de pruebas y rechaza antes de crear el engine cualquier URL PostgreSQL que no tenga el prefijo temporal `atanes_test_`. Por eso, incluso una ejecución directa de tests no puede escribir en la base principal `Linkedin`.

El runner crea una base PostgreSQL local temporal, configura `DATABASE_URL` antes de importar la aplicación, ejecuta la suite y elimina únicamente esa base temporal. No usa la base principal configurada para desarrollo.

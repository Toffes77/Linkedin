"""Importa incrementalmente las publicaciones definidas en ``Mas datos.md``.

Uso desde la raiz del repositorio:

    python backend/scripts/importar_publicaciones_mas_datos.py --dry-run
    python backend/scripts/importar_publicaciones_mas_datos.py --apply

La carga es transaccional e idempotente por la combinacion exacta autor/texto.
Solo opera contra la base local ``Linkedin`` en entorno ``development``.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_DIR = BACKEND_DIR.parent
SOURCE_PATH = REPOSITORY_DIR / "Mas datos.md"

COMPANY_SECTION = "Publicaciones cuyo dueño hay que buscar"
PERSON_SECTION = "Publicaciones cuyo dueño no hay que buscar"

# Son equivalencias explicitas verificadas contra los nombres del seed. No se
# usa matching parcial ni fuzzy para resolver nombres corporativos abreviados.
COMPANY_AUTHORS = (
    ("Banco Marcelo", "Banco Marcelo"),
    ("Ensamblajes Freier", "Ensamblajes de PCs Freier"),
    ("Centro de Proctología", "Centro de Proctología ZUZU"),
    ("Explosivos Cañopos", "Explosivos Cañopos"),
    ("PrestaYa", "PrestaYa"),
    ("Maped", "Maped"),
    ("Carrefour", "Carrefour"),
    ("Makro", "Makro Argentina"),
    ("Amazon", "Amazon"),
    ("Coca-Cola", "The Coca-Cola Company"),
)

PERSON_AUTHORS = (
    ("Agustín Pelachini", "Agustín Pelachini"),
    ("Benjamin Jerez", "Benjamin Jerez"),
    ("Binyamin Al-Ghomiz", "Binyamin Al-Ghomiz"),
    (
        "Ignacio Libermann — CEO en Veterinaria de Gatos Rescatados",
        "Ignacio Libermann",
    ),
    ("Joaquín Gambeta — Proctólogo", "Joaquín Gambeta"),
    ("Juan Cruz Maletti — Ingeniero Mecánico", "Juan Cruz Maletti"),
    ("Juan Cruz Moyano — Presidente de Compañía", "Juan Cruz Moyano"),
    (
        "Lorenzo Díaz — Empresario en Telecomunicaciones",
        "Lorenzo Díaz",
    ),
    ("Luca Di Lauro — CEO de Empresas Prestamistas", "Luca Di Lauro"),
    ("Lucas Estevo — Empleado en Concesionaria", "Lucas Estevo"),
    ("Manuel Valle — Director de Pymes", "Manuel Valle"),
    ("Santín Ben-Konka — Director de Bancaria", "Santín Ben-Konka"),
    ("Fernando Mayer", "Fernando Mayer"),
    ("Franco Ghirardi", "Franco Ghirardi"),
    ("Gael Ponce", "Gael Ponce"),
)

DOMAIN_TABLES = (
    "comentario",
    "conexiones",
    "conversacion",
    "conversacion_usuario",
    "empresa",
    "empresa_usuario",
    "experiencia",
    "mensaje",
    "notificacion",
    "oferta",
    "postulacion",
    "promocion",
    "publicacion",
    "reacciones",
    "seguimiento",
    "solicitud_contratacion_promocion",
    "usuario",
)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

import src.app  # noqa: E402,F401 - registra todos los modelos relacionados
from sqlalchemy import text  # noqa: E402

from src.db.connection import SessionLocal  # noqa: E402
from src.db.models.empresa_model import Empresa  # noqa: E402
from src.db.models.empresa_usuario_model import (  # noqa: E402
    EmpresaUsuario,
    RolEmpresa,
)
from src.db.models.publicacion_model import Publicacion  # noqa: E402
from src.db.models.usuario_model import Usuario  # noqa: E402
from src.dtos.publicacion_dto import CreatePublicacionDTO  # noqa: E402
from src.mappers.publicacion_mapper import PublicacionMapper  # noqa: E402
from src.utils.datetime_utils import utc_now  # noqa: E402


@dataclass(frozen=True)
class SourceEntry:
    order: int
    indicated_author: str
    lookup_name: str
    author_type: str
    text: str


@dataclass(frozen=True)
class ResolvedEntry:
    source: SourceEntry
    user_id: int
    user_name: str
    company_id: int | None = None
    company_name: str | None = None
    owner_candidates: tuple[tuple[int, str], ...] = ()


def normalize_identity(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    without_dashes = re.sub(r"[-‐-―]", " ", without_accents)
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", without_dashes.casefold()).split()
    )


def _section_body(document: str, start_heading: str, end_heading: str | None) -> str:
    start_pattern = re.compile(rf"(?m)^{re.escape(start_heading)}[ \t]*$")
    matches = list(start_pattern.finditer(document))
    if len(matches) != 1:
        raise ValueError(
            f"Se esperaba una aparicion de la seccion {start_heading!r}; hay {len(matches)}"
        )
    body_start = matches[0].end()
    if end_heading is None:
        return document[body_start:]

    end_pattern = re.compile(rf"(?m)^{re.escape(end_heading)}[ \t]*$")
    end_matches = [match for match in end_pattern.finditer(document) if match.start() > body_start]
    if len(end_matches) != 1:
        raise ValueError(
            f"Se esperaba una aparicion posterior de {end_heading!r}; hay {len(end_matches)}"
        )
    return document[body_start : end_matches[0].start()]


def _extract_section_entries(
    body: str,
    author_type: str,
    author_specs: tuple[tuple[str, str], ...],
    start_order: int,
) -> list[SourceEntry]:
    positions: list[tuple[int, int, str, str]] = []
    for marker, lookup_name in author_specs:
        pattern = re.compile(rf"(?m)^{re.escape(marker)}[ \t]*$")
        matches = list(pattern.finditer(body))
        if len(matches) != 1:
            raise ValueError(
                f"Se esperaba exactamente un marcador de autor {marker!r}; hay {len(matches)}"
            )
        match = matches[0]
        positions.append((match.start(), match.end(), marker, lookup_name))

    if positions != sorted(positions):
        raise ValueError(f"Los autores de la seccion {author_type} cambiaron de orden")

    leading = body[: positions[0][0]].strip()
    if leading:
        raise ValueError(f"Contenido sin autor antes de la seccion {author_type}: {leading!r}")

    entries: list[SourceEntry] = []
    for index, (_, marker_end, marker, lookup_name) in enumerate(positions):
        content_end = positions[index + 1][0] if index + 1 < len(positions) else len(body)
        publication_text = body[marker_end:content_end].strip()
        if not publication_text:
            raise ValueError(f"Publicacion sin texto para {marker!r}")
        entries.append(
            SourceEntry(
                order=start_order + index,
                indicated_author=marker,
                lookup_name=lookup_name,
                author_type=author_type,
                text=publication_text,
            )
        )
    return entries


def parse_source() -> list[SourceEntry]:
    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(SOURCE_PATH)
    document = SOURCE_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    if document.startswith("\ufeff"):
        document = document.removeprefix("\ufeff")

    company_body = _section_body(document, COMPANY_SECTION, PERSON_SECTION)
    person_body = _section_body(document, PERSON_SECTION, None)
    company_entries = _extract_section_entries(
        company_body,
        "empresa",
        COMPANY_AUTHORS,
        0,
    )
    person_entries = _extract_section_entries(
        person_body,
        "persona",
        PERSON_AUTHORS,
        len(company_entries),
    )
    entries = company_entries + person_entries

    duplicate_sources = {
        (entry.author_type, normalize_identity(entry.lookup_name), entry.text)
        for entry in entries
    }
    if len(duplicate_sources) != len(entries):
        raise ValueError("Mas datos.md contiene publicaciones duplicadas para el mismo autor")
    return entries


def assert_safe_database(db) -> dict[str, object]:
    from src.config.env import settings

    configured = urlparse(settings.DATABASE_URL)
    if settings.ENVIRONMENT.casefold() != "development":
        raise RuntimeError("Importacion abortada: ENVIRONMENT no es development")
    if configured.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Importacion abortada: DATABASE_URL no apunta a loopback")
    if configured.path.lstrip("/") != "Linkedin":
        raise RuntimeError("Importacion abortada: DATABASE_URL no apunta a Linkedin")

    database, server_address, server_port = db.execute(
        text("SELECT current_database(), inet_server_addr()::text, inet_server_port()")
    ).one()
    if database != "Linkedin":
        raise RuntimeError("Importacion abortada: la base efectiva no es Linkedin")
    if server_address is None or not ipaddress.ip_interface(server_address).ip.is_loopback:
        raise RuntimeError("Importacion abortada: PostgreSQL no esta en loopback")
    return {
        "database": database,
        "server_address": server_address,
        "server_port": server_port,
        "environment": settings.ENVIRONMENT,
    }


def table_counts(db) -> dict[str, int]:
    return {
        table_name: db.execute(
            text(f'SELECT count(*) FROM public."{table_name}"')
        ).scalar_one()
        for table_name in DOMAIN_TABLES
    }


def table_fingerprints(db) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for table_name in DOMAIN_TABLES:
        if table_name == "publicacion":
            continue
        rows = db.execute(
            text(
                f'SELECT row_to_json(item)::text FROM public."{table_name}" AS item '
                "ORDER BY row_to_json(item)::text"
            )
        ).scalars()
        digest = hashlib.sha256()
        for row in rows:
            digest.update(row.encode("utf-8"))
            digest.update(b"\n")
        fingerprints[table_name] = digest.hexdigest()
    return fingerprints


def schema_fingerprint(db) -> str:
    queries = (
        """
        SELECT table_name, ordinal_position, column_name, data_type, udt_name,
               is_nullable, COALESCE(column_default, ''),
               COALESCE(character_maximum_length::text, '')
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
        """,
        """
        SELECT c.relname, con.conname, con.contype,
               pg_get_constraintdef(con.oid, true)
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
        ORDER BY c.relname, con.conname
        """,
        """
        SELECT tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
        """,
    )
    digest = hashlib.sha256()
    for query in queries:
        for row in db.execute(text(query)):
            digest.update(json.dumps(list(row), ensure_ascii=False).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def _unique_normalized(items, name_attribute: str, kind: str):
    grouped: dict[str, list[object]] = {}
    for item in items:
        grouped.setdefault(
            normalize_identity(getattr(item, name_attribute)), []
        ).append(item)
    ambiguous = {key: values for key, values in grouped.items() if len(values) != 1}
    if ambiguous:
        raise RuntimeError(f"Hay nombres normalizados ambiguos de {kind}: {sorted(ambiguous)}")
    return {key: values[0] for key, values in grouped.items()}


def resolve_entries(db, source_entries: list[SourceEntry]) -> list[ResolvedEntry]:
    users = db.query(Usuario).order_by(Usuario.id).all()
    companies = db.query(Empresa).order_by(Empresa.id).all()
    users_by_name = _unique_normalized(users, "nombre", "usuario")
    companies_by_name = _unique_normalized(companies, "nombre", "empresa")

    resolved: list[ResolvedEntry] = []
    for entry in source_entries:
        if entry.author_type == "persona":
            user = users_by_name.get(normalize_identity(entry.lookup_name))
            if user is None:
                raise RuntimeError(
                    f"Autor-persona no resuelto inequívocamente: {entry.lookup_name!r}"
                )
            resolved.append(
                ResolvedEntry(
                    source=entry,
                    user_id=user.id,
                    user_name=user.nombre,
                )
            )
            continue

        company = companies_by_name.get(normalize_identity(entry.lookup_name))
        if company is None:
            raise RuntimeError(
                f"Autor-empresa no resuelto inequívocamente: {entry.lookup_name!r}"
            )
        owner_rows = (
            db.query(Usuario.id, Usuario.nombre)
            .join(EmpresaUsuario, EmpresaUsuario.usuario_id == Usuario.id)
            .filter(
                EmpresaUsuario.empresa_id == company.id,
                EmpresaUsuario.rol == RolEmpresa.OWNER,
            )
            .order_by(Usuario.id)
            .all()
        )
        if not owner_rows:
            raise RuntimeError(f"La empresa {company.nombre!r} no tiene OWNER")
        owner_candidates = tuple((row.id, row.nombre) for row in owner_rows)
        chosen_id, chosen_name = owner_candidates[0]
        resolved.append(
            ResolvedEntry(
                source=entry,
                user_id=chosen_id,
                user_name=chosen_name,
                company_id=company.id,
                company_name=company.nombre,
                owner_candidates=owner_candidates,
            )
        )

    source_pairs = {(entry.user_id, entry.source.text) for entry in resolved}
    if len(source_pairs) != len(resolved):
        raise RuntimeError("Dos entradas se resolverian al mismo autor y texto")

    for entry in resolved:
        CreatePublicacionDTO(autor_id=entry.user_id, texto=entry.source.text)
    return resolved


def publication_status(db, entry: ResolvedEntry) -> tuple[str, int | None]:
    matches = (
        db.query(Publicacion.id)
        .filter(
            Publicacion.autor_id == entry.user_id,
            Publicacion.texto == entry.source.text,
        )
        .order_by(Publicacion.id)
        .all()
    )
    if len(matches) > 1:
        raise RuntimeError(
            f"Ya hay {len(matches)} duplicados exactos para {entry.source.indicated_author!r}"
        )
    if matches:
        return "omitida_por_duplicado", matches[0].id
    return "lista_para_insertar", None


def entry_report(db, entry: ResolvedEntry) -> dict[str, object]:
    status, existing_id = publication_status(db, entry)
    report: dict[str, object] = {
        "orden": entry.source.order + 1,
        "autor_indicado": entry.source.indicated_author,
        "tipo_detectado": entry.source.author_type,
        "usuario_real_id": entry.user_id,
        "usuario_real": entry.user_name,
        "texto": entry.source.text,
        "caracteres": len(entry.source.text),
        "estado": status,
        "publicacion_id": existing_id,
    }
    if entry.company_id is not None:
        report.update(
            {
                "empresa_id": entry.company_id,
                "empresa": entry.company_name,
                "owners_disponibles": [
                    {"usuario_id": owner_id, "nombre": owner_name}
                    for owner_id, owner_name in entry.owner_candidates
                ],
                "criterio_owner": "menor usuario_id",
            }
        )
    return report


def build_dry_run(db) -> tuple[list[ResolvedEntry], dict[str, object]]:
    database = assert_safe_database(db)
    source_entries = parse_source()
    resolved = resolve_entries(db, source_entries)
    reports = [entry_report(db, entry) for entry in resolved]
    return resolved, {
        "mode": "dry-run; PostgreSQL no fue modificado",
        "source": str(SOURCE_PATH),
        "database": database,
        "counts": table_counts(db),
        "total_encontradas": len(reports),
        "autores_persona": sum(
            report["tipo_detectado"] == "persona" for report in reports
        ),
        "autores_empresa": sum(
            report["tipo_detectado"] == "empresa" for report in reports
        ),
        "listas_para_insertar": sum(
            report["estado"] == "lista_para_insertar" for report in reports
        ),
        "omitidas_por_duplicado": sum(
            report["estado"] == "omitida_por_duplicado" for report in reports
        ),
        "no_resueltas": 0,
        "publicaciones": reports,
    }


def apply_import(db, resolved: list[ResolvedEntry]) -> dict[str, object]:
    # Evita que dos ejecuciones concurrentes pasen a la vez el control de duplicados.
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('atanes:mas-datos-publicaciones'))"))
    assert_safe_database(db)

    counts_before = table_counts(db)
    rows_before = table_fingerprints(db)
    schema_before = schema_fingerprint(db)
    pending: list[ResolvedEntry] = []
    duplicates: list[dict[str, object]] = []
    for entry in resolved:
        status, existing_id = publication_status(db, entry)
        if status == "omitida_por_duplicado":
            duplicates.append(
                {
                    "autor_indicado": entry.source.indicated_author,
                    "usuario_real": entry.user_name,
                    "publicacion_id": existing_id,
                }
            )
        else:
            pending.append(entry)

    created_models: list[tuple[ResolvedEntry, Publicacion]] = []
    base_date = utc_now()
    for entry in pending:
        dto = CreatePublicacionDTO(
            autor_id=entry.user_id,
            texto=entry.source.text,
        )
        model = PublicacionMapper.to_model(dto)
        # El primer texto del archivo queda mas reciente; todos son UTC-aware y
        # ninguno queda en el futuro.
        model.fecha = base_date - timedelta(seconds=entry.source.order)
        db.add(model)
        created_models.append((entry, model))

    db.flush()
    counts_after = table_counts(db)
    rows_after = table_fingerprints(db)
    schema_after = schema_fingerprint(db)

    expected_publications = counts_before["publicacion"] + len(pending)
    if counts_after["publicacion"] != expected_publications:
        raise RuntimeError("El conteo de publicaciones no aumento como se esperaba")
    unchanged_counts = {
        name: counts_after[name] == count
        for name, count in counts_before.items()
        if name != "publicacion"
    }
    if not all(unchanged_counts.values()):
        raise RuntimeError("Cambio inesperado en el conteo de otra tabla")
    if rows_after != rows_before:
        raise RuntimeError("Cambio inesperado en los datos de otra tabla")
    if schema_after != schema_before:
        raise RuntimeError("Cambio inesperado en el esquema")

    created = [
        {
            "id": model.id,
            "autor_indicado": entry.source.indicated_author,
            "usuario_real_id": entry.user_id,
            "usuario_real": entry.user_name,
            "empresa_origen": entry.company_name,
            "texto": model.texto,
            "fecha": model.fecha.isoformat(),
        }
        for entry, model in created_models
    ]
    db.commit()

    persisted_ids = [item["id"] for item in created]
    persisted_count = (
        db.query(Publicacion).filter(Publicacion.id.in_(persisted_ids)).count()
        if persisted_ids
        else 0
    )
    if persisted_count != len(created):
        raise RuntimeError("No se pudieron verificar todas las publicaciones persistidas")

    return {
        "insertadas": len(created),
        "omitidas_por_duplicado": len(duplicates),
        "no_resueltas": 0,
        "publicaciones_creadas": created,
        "duplicados": duplicates,
        "counts_before": counts_before,
        "counts_after": counts_after,
        "otras_tablas_sin_cambios": all(unchanged_counts.values())
        and rows_after == rows_before,
        "schema_sin_cambios": schema_after == schema_before,
        "schema_fingerprint": schema_after,
        "persistidas_verificadas": persisted_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        try:
            resolved, dry_run = build_dry_run(db)
            if args.dry_run:
                output = dry_run
            else:
                output = {
                    "source": str(SOURCE_PATH),
                    "database": dry_run["database"],
                    "preflight": {
                        key: dry_run[key]
                        for key in (
                            "total_encontradas",
                            "autores_persona",
                            "autores_empresa",
                            "listas_para_insertar",
                            "omitidas_por_duplicado",
                            "no_resueltas",
                        )
                    },
                    "import": apply_import(db, resolved),
                }
        except Exception:
            db.rollback()
            raise
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

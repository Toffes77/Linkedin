"""Agrega ofertas laborales ficticias y publicadas a las empresas existentes.

Uso desde la raiz del repositorio:

    python backend/scripts/generar_ofertas_seed.py --dry-run
    python backend/scripts/generar_ofertas_seed.py --apply

El seed es transaccional e idempotente por empresa y titulo. Solo opera contra
la base local ``Linkedin`` en entorno ``development``.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

import src.app  # noqa: E402,F401 - registra todos los modelos relacionados
from sqlalchemy import text  # noqa: E402

from src.db.connection import SessionLocal  # noqa: E402
from src.db.models.empresa_model import Empresa  # noqa: E402
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa  # noqa: E402
from src.db.models.oferta_model import Oferta  # noqa: E402
from src.db.models.usuario_model import Usuario  # noqa: E402
from src.dtos.oferta_dto import CreateOfertaDTO  # noqa: E402
from src.mappers.oferta_mapper import OfertaMapper  # noqa: E402
from src.utils.datetime_utils import utc_now  # noqa: E402


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

SEED_REFERENCE_DATE = datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class OfferSpec:
    title: str
    location: str
    description: str


@dataclass(frozen=True)
class CompanySpec:
    offers: tuple[OfferSpec, ...]


def offer(title: str, location: str, responsibilities: str, requirements: str) -> OfferSpec:
    description = (
        f"{responsibilities}\n\n"
        f"Perfil buscado: {requirements}\n\n"
        f"Ubicación: {location}."
    )
    return OfferSpec(title=title, location=location, description=description)


COMPANIES: dict[str, CompanySpec] = {
    "Amazon": CompanySpec(
        (
            offer(
                "Ingeniero/a de Software Backend",
                "Estados Unidos, Seattle",
                "Diseñará servicios distribuidos para plataformas de comercio y nube, mejorará su observabilidad y participará en revisiones técnicas orientadas a confiabilidad y rendimiento.",
                "experiencia con Python, Java o lenguajes equivalentes, APIs, bases de datos y sistemas escalables; capacidad para comunicar decisiones de arquitectura.",
            ),
            offer(
                "Especialista en Operaciones Logísticas",
                "Argentina, Buenos Aires",
                "Analizará capacidad, tiempos de entrega y desvíos operativos en centros de distribución. Coordinará mejoras con equipos de transporte, inventario y atención al cliente.",
                "experiencia en logística o ingeniería industrial, manejo de indicadores y herramientas de análisis, y criterio para priorizar incidentes operativos.",
            ),
        )
    ),
    "Banco Marcelo": CompanySpec(
        (
            offer(
                "Analista de Riesgo Crediticio",
                "Argentina, Buenos Aires",
                "Evaluará solicitudes de crédito, monitoreará la calidad de cartera y preparará escenarios para acompañar decisiones comerciales responsables.",
                "formación en finanzas, economía o áreas afines, manejo de datos y conocimiento general de riesgo, regulación y documentación crediticia.",
            ),
        )
    ),
    "Carrefour": CompanySpec(
        (
            offer(
                "Supervisor/a de Operaciones de Tienda",
                "Argentina, Córdoba",
                "Coordinará equipos de piso, reposición y cajas, cuidando disponibilidad, experiencia del cliente y cumplimiento de procedimientos durante cada turno.",
                "experiencia en retail u operaciones, organización de equipos, lectura de indicadores y disponibilidad para trabajar con distintas áreas de la tienda.",
            ),
            offer(
                "Especialista en Marketing y Fidelización",
                "Argentina, Buenos Aires",
                "Diseñará campañas segmentadas para clientes frecuentes, analizará resultados y colaborará con comercial y datos para mejorar relevancia y recurrencia.",
                "experiencia en marketing digital, CRM y análisis de campañas; redacción clara y capacidad para convertir hallazgos en acciones medibles.",
            ),
        )
    ),
    "Centro de Proctología ZUZU": CompanySpec(
        (
            offer(
                "Coordinador/a de Atención al Paciente",
                "Argentina, Rosario",
                "Organizará turnos, derivaciones y comunicación previa y posterior a las consultas, preservando privacidad, claridad y una experiencia respetuosa para cada paciente.",
                "experiencia en administración de salud o atención, excelente comunicación, manejo responsable de información y capacidad para coordinar agendas clínicas.",
            ),
        )
    ),
    "EA Sports": CompanySpec(
        (
            offer(
                "Desarrollador/a de Gameplay",
                "Canadá, Vancouver",
                "Implementará mecánicas deportivas, herramientas de simulación y mejoras de respuesta en controles, trabajando junto a diseño, animación y control de calidad.",
                "experiencia con C++ o C#, fundamentos de matemática aplicada a videojuegos y capacidad para iterar a partir de pruebas de jugabilidad.",
            ),
            offer(
                "Analista de Datos de Jugabilidad",
                "España, Madrid",
                "Estudiará patrones de uso, balance y progresión para detectar fricciones y oportunidades de mejora sin perder de vista la experiencia completa del jugador.",
                "SQL, visualización de datos, estadística aplicada y habilidad para explicar resultados a equipos de producto y diseño.",
            ),
        )
    ),
    "Ensamblajes de PCs Freier": CompanySpec(
        (
            offer(
                "Técnico/a de Ensamblaje y Soporte de PCs",
                "Argentina, Córdoba",
                "Ensamblará equipos a medida, realizará pruebas térmicas y de estabilidad, documentará configuraciones y diagnosticará fallas de hardware para clientes y pymes.",
                "conocimiento práctico de componentes, compatibilidad, BIOS, sistemas operativos y herramientas de diagnóstico; trato claro con usuarios no técnicos.",
            ),
        )
    ),
    "Explosivos Cañopos": CompanySpec(
        (
            offer(
                "Ingeniero/a de Seguridad en Voladuras",
                "Argentina, Mendoza",
                "Participará en la planificación y control de voladuras, revisará parámetros críticos y coordinará registros de seguridad, instrumentación y mejora posterior a cada operación.",
                "formación en ingeniería o minería, experiencia en operaciones de campo, análisis de riesgos y compromiso estricto con procedimientos y trazabilidad.",
            ),
        )
    ),
    "Makro Argentina": CompanySpec(
        (
            offer(
                "Analista de Abastecimiento Mayorista",
                "Argentina, Buenos Aires",
                "Planificará reposición para categorías de alto volumen, analizará quiebres y rotación, y coordinará con proveedores y tiendas acciones para mejorar disponibilidad.",
                "experiencia en abastecimiento, compras o planificación, dominio de hojas de cálculo y análisis de datos, y capacidad de negociación y seguimiento.",
            ),
        )
    ),
    "Maped": CompanySpec(
        (
            offer(
                "Diseñador/a Industrial de Productos Escolares",
                "Francia, Annecy",
                "Desarrollará conceptos de útiles y accesorios escolares, construirá prototipos y evaluará ergonomía, durabilidad y experiencia de uso con equipos de producto.",
                "formación en diseño industrial, manejo de modelado y prototipado, sensibilidad por color y materiales, y capacidad para documentar decisiones.",
            ),
            offer(
                "Ingeniero/a de Procesos de Producción",
                "Argentina, Buenos Aires",
                "Optimizará procesos de fabricación y control de calidad, investigará desvíos y acompañará la introducción de nuevos productos en líneas productivas.",
                "formación en ingeniería industrial, mecánica o afín, experiencia con mejora continua, análisis de causa raíz y coordinación con producción y calidad.",
            ),
        )
    ),
    "McDonald's": CompanySpec(
        (
            offer(
                "Supervisor/a de Operaciones de Restaurantes",
                "Argentina, Buenos Aires",
                "Acompañará equipos de turno, verificará estándares de servicio, seguridad alimentaria e inventario, y dará seguimiento a planes de mejora de cada restaurante.",
                "experiencia liderando operaciones o atención al cliente, organización en entornos dinámicos y habilidad para formar y dar retroalimentación a equipos.",
            ),
        )
    ),
    "OpenAI": CompanySpec(
        (
            offer(
                "Ingeniero/a de Aprendizaje Automático",
                "Estados Unidos, San Francisco",
                "Construirá sistemas para entrenar, evaluar y desplegar modelos, mejorará pipelines de datos y colaborará con investigación e infraestructura para convertir experimentos en productos confiables.",
                "experiencia con Python, aprendizaje automático, evaluación de modelos y sistemas distribuidos; criterio para medir calidad, costo y seguridad.",
            ),
            offer(
                "Investigador/a en Seguridad de IA",
                "Estados Unidos, San Francisco",
                "Diseñará evaluaciones para detectar comportamientos no deseados, analizará resultados y propondrá mitigaciones reproducibles junto a equipos técnicos y de políticas.",
                "experiencia en investigación empírica, estadística o machine learning, escritura rigurosa y capacidad para trabajar con problemas abiertos y evidencia incompleta.",
            ),
        )
    ),
    "PrestaYa": CompanySpec(
        (
            offer(
                "Analista de Producto Crediticio Digital",
                "Argentina, Buenos Aires",
                "Analizará el recorrido de solicitud, reglas de elegibilidad y desempeño de productos de crédito para proponer mejoras claras, responsables y medibles.",
                "experiencia en producto, fintech o análisis de negocio, manejo de métricas y conocimiento general de riesgo, experiencia de usuario y regulación financiera.",
            ),
        )
    ),
    "The Coca-Cola Company": CompanySpec(
        (
            offer(
                "Especialista en Calidad de Procesos",
                "Argentina, Buenos Aires",
                "Monitoreará controles de calidad, investigará desvíos y coordinará acciones preventivas con producción, laboratorios, logística y proveedores.",
                "formación en alimentos, química, ingeniería o áreas relacionadas, experiencia con sistemas de calidad, documentación y análisis de causa raíz.",
            ),
            offer(
                "Coordinador/a de Marketing de Marca",
                "México, Ciudad de México",
                "Coordinará campañas de marca, activaciones y materiales para distintos canales, asegurando consistencia creativa y seguimiento de resultados comerciales.",
                "experiencia en marketing de consumo masivo, gestión de proyectos y agencias, análisis de campañas y comunicación efectiva con equipos regionales.",
            ),
        )
    ),
}


def publication_date(company_id: int, offer_index: int) -> datetime:
    return SEED_REFERENCE_DATE - timedelta(
        days=(company_id * 3 + offer_index * 5) % 15,
        hours=(company_id + offer_index * 2) % 8,
        minutes=company_id * 2 + offer_index * 7,
    )


def assert_safe_database(db) -> dict[str, object]:
    from src.config.env import settings

    configured = urlparse(settings.DATABASE_URL)
    if settings.ENVIRONMENT.casefold() != "development":
        raise RuntimeError("Seed abortado: ENVIRONMENT no es development")
    if configured.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Seed abortado: DATABASE_URL no apunta a loopback")
    if configured.path.lstrip("/") != "Linkedin":
        raise RuntimeError("Seed abortado: DATABASE_URL no apunta a Linkedin")

    database, address, port = db.execute(
        text("SELECT current_database(), inet_server_addr()::text, inet_server_port()")
    ).one()
    if database != "Linkedin" or not ipaddress.ip_interface(address).ip.is_loopback:
        raise RuntimeError("Seed abortado: PostgreSQL efectivo no es Linkedin local")
    return {
        "database": database,
        "server_address": address,
        "server_port": port,
        "environment": settings.ENVIRONMENT,
    }


def table_counts(db) -> dict[str, int]:
    return {
        table_name: db.execute(
            text(f'SELECT count(*) FROM public."{table_name}"')
        ).scalar_one()
        for table_name in DOMAIN_TABLES
    }


def other_table_fingerprints(db) -> dict[str, str]:
    result: dict[str, str] = {}
    for table_name in DOMAIN_TABLES:
        if table_name == "oferta":
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
        result[table_name] = digest.hexdigest()
    return result


def existing_offer_snapshot(db) -> dict[int, tuple[object, ...]]:
    return {
        item.id: (
            item.empresa_id,
            item.titulo,
            item.descripcion,
            item.publicada,
            item.fecha_publicacion,
        )
        for item in db.query(Oferta).order_by(Oferta.id)
    }


def validate_manifest(db):
    companies = db.query(Empresa).order_by(Empresa.id).all()
    companies_by_name = {company.nombre: company for company in companies}
    if len(companies_by_name) != len(companies):
        raise RuntimeError("Hay nombres de empresa duplicados")
    if set(companies_by_name) != set(COMPANIES):
        raise RuntimeError(
            f"Empresas esperadas: {sorted(COMPANIES)}; actuales: {sorted(companies_by_name)}"
        )

    owner_by_company: dict[int, Usuario] = {}
    for company in companies:
        owners = (
            db.query(Usuario)
            .join(EmpresaUsuario, EmpresaUsuario.usuario_id == Usuario.id)
            .filter(
                EmpresaUsuario.empresa_id == company.id,
                EmpresaUsuario.rol == RolEmpresa.OWNER,
            )
            .order_by(Usuario.id)
            .all()
        )
        if not owners:
            raise RuntimeError(f"{company.nombre} no tiene OWNER")
        owner_by_company[company.id] = owners[0]

    distribution = Counter(len(spec.offers) for spec in COMPANIES.values())
    if distribution != {1: 7, 2: 6}:
        raise RuntimeError(f"Distribucion de ofertas inesperada: {distribution}")

    seen_titles: set[tuple[str, str]] = set()
    now = utc_now()
    for company_name, company_spec in COMPANIES.items():
        company = companies_by_name[company_name]
        if not 1 <= len(company_spec.offers) <= 2:
            raise RuntimeError(f"Cantidad invalida para {company_name}")
        for offer_index, offer_spec in enumerate(company_spec.offers):
            if (company_name, offer_spec.title) in seen_titles:
                raise RuntimeError("Titulo repetido dentro del seed")
            seen_titles.add((company_name, offer_spec.title))
            if not offer_spec.location or ", " not in offer_spec.location:
                raise RuntimeError(f"Ubicacion invalida: {offer_spec.location}")
            dto = CreateOfertaDTO(
                empresa_id=company.id,
                titulo=offer_spec.title,
                descripcion=offer_spec.description,
                publicada=True,
                fecha_publicacion=publication_date(company.id, offer_index),
            )
            if not dto.publicada or dto.fecha_publicacion is None:
                raise RuntimeError("Oferta no publicada o sin fecha")
            if dto.fecha_publicacion.utcoffset() is None or dto.fecha_publicacion > now:
                raise RuntimeError("Fecha naive o futura")
            if f"Ubicación: {offer_spec.location}." not in dto.descripcion:
                raise RuntimeError("La descripcion no conserva la ubicacion")
    return companies_by_name, owner_by_company


def find_seed_offer(db, company_id: int, offer_spec: OfferSpec):
    matches = (
        db.query(Oferta)
        .filter(Oferta.empresa_id == company_id, Oferta.titulo == offer_spec.title)
        .order_by(Oferta.id)
        .all()
    )
    if len(matches) > 1:
        raise RuntimeError("Hay ofertas duplicadas con el mismo titulo y empresa")
    if not matches:
        return None
    existing = matches[0]
    if existing.descripcion != offer_spec.description or not existing.publicada:
        raise RuntimeError(
            f"Conflicto: ya existe {offer_spec.title!r} con datos diferentes"
        )
    if existing.fecha_publicacion is None:
        raise RuntimeError("Oferta existente del seed sin fecha de publicacion")
    return existing


def dry_run_report(db, companies_by_name, owner_by_company) -> dict[str, object]:
    companies_report = []
    pending = duplicates = 0
    for company_name, company_spec in COMPANIES.items():
        company = companies_by_name[company_name]
        owner = owner_by_company[company.id]
        offers_report = []
        for offer_index, offer_spec in enumerate(company_spec.offers):
            existing = find_seed_offer(db, company.id, offer_spec)
            pending += existing is None
            duplicates += existing is not None
            offers_report.append(
                {
                    "id": existing.id if existing else None,
                    "titulo": offer_spec.title,
                    "ubicacion_en_descripcion": offer_spec.location,
                    "descripcion": offer_spec.description,
                    "publicada": True,
                    "fecha_publicacion": (
                        existing.fecha_publicacion if existing else publication_date(company.id, offer_index)
                    ).isoformat(),
                    "estado": "duplicada" if existing else "lista_para_insertar",
                }
            )
        companies_report.append(
            {
                "empresa_id": company.id,
                "empresa": company.nombre,
                "industria_actual": company.industria,
                "owner_utilizado_id": owner.id,
                "owner_utilizado": owner.nombre,
                "ofertas": offers_report,
            }
        )
    return {
        "empresas": companies_report,
        "ofertas_definidas": sum(len(spec.offers) for spec in COMPANIES.values()),
        "ofertas_pendientes": pending,
        "ofertas_duplicadas": duplicates,
        "empresas_con_una": sum(len(spec.offers) == 1 for spec in COMPANIES.values()),
        "empresas_con_dos": sum(len(spec.offers) == 2 for spec in COMPANIES.values()),
    }


def sql_verifications(db, seed_offer_ids: list[int]) -> dict[str, object]:
    seed_count = len(seed_offer_ids)
    values = {
        "empresas": db.execute(text("SELECT count(*) FROM empresa")).scalar_one(),
        "empresas_sin_oferta_publicada": db.execute(
            text(
                "SELECT count(*) FROM empresa e WHERE NOT EXISTS "
                "(SELECT 1 FROM oferta o WHERE o.empresa_id=e.id AND o.publicada)"
            )
        ).scalar_one(),
        "seed_sin_empresa": db.execute(
            text(
                "SELECT count(*) FROM oferta o LEFT JOIN empresa e ON e.id=o.empresa_id "
                "WHERE o.id=ANY(:ids) AND e.id IS NULL"
            ),
            {"ids": seed_offer_ids},
        ).scalar_one(),
        "seed_no_publicadas": db.execute(
            text("SELECT count(*) FROM oferta WHERE id=ANY(:ids) AND NOT publicada"),
            {"ids": seed_offer_ids},
        ).scalar_one(),
        "seed_sin_fecha": db.execute(
            text("SELECT count(*) FROM oferta WHERE id=ANY(:ids) AND fecha_publicacion IS NULL"),
            {"ids": seed_offer_ids},
        ).scalar_one(),
        "seed_fechas_futuras": db.execute(
            text("SELECT count(*) FROM oferta WHERE id=ANY(:ids) AND fecha_publicacion>now()"),
            {"ids": seed_offer_ids},
        ).scalar_one(),
        "seed_titulos_vacios": db.execute(
            text("SELECT count(*) FROM oferta WHERE id=ANY(:ids) AND titulo !~ '[^[:space:]]'"),
            {"ids": seed_offer_ids},
        ).scalar_one(),
        "seed_descripciones_vacias": db.execute(
            text("SELECT count(*) FROM oferta WHERE id=ANY(:ids) AND descripcion !~ '[^[:space:]]'"),
            {"ids": seed_offer_ids},
        ).scalar_one(),
        "seed_duplicados": db.execute(
            text(
                "SELECT count(*) FROM (SELECT empresa_id,titulo FROM oferta "
                "WHERE id=ANY(:ids) GROUP BY empresa_id,titulo HAVING count(*)>1) d"
            ),
            {"ids": seed_offer_ids},
        ).scalar_one(),
        "postulaciones": db.execute(text("SELECT count(*) FROM postulacion")).scalar_one(),
        "seed_verificado": db.execute(
            text("SELECT count(*) FROM oferta WHERE id=ANY(:ids)"),
            {"ids": seed_offer_ids},
        ).scalar_one(),
    }
    zero_fields = (
        "empresas_sin_oferta_publicada",
        "seed_sin_empresa",
        "seed_no_publicadas",
        "seed_sin_fecha",
        "seed_fechas_futuras",
        "seed_titulos_vacios",
        "seed_descripciones_vacias",
        "seed_duplicados",
        "postulaciones",
    )
    if values["empresas"] != 13 or any(values[key] for key in zero_fields):
        raise RuntimeError(f"Fallo una verificacion SQL: {values}")
    if values["seed_verificado"] != seed_count:
        raise RuntimeError("No se encontraron todas las ofertas del seed")
    return values


def apply_seed(db, companies_by_name, owner_by_company) -> dict[str, object]:
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('atanes:ofertas-seed'))"))
    assert_safe_database(db)
    counts_before = table_counts(db)
    other_rows_before = other_table_fingerprints(db)
    existing_before = existing_offer_snapshot(db)
    created: list[Oferta] = []
    duplicates = 0

    for company_name, company_spec in COMPANIES.items():
        company = companies_by_name[company_name]
        owner = owner_by_company[company.id]
        has_owner_role = (
            db.query(EmpresaUsuario)
            .filter(
                EmpresaUsuario.empresa_id == company.id,
                EmpresaUsuario.usuario_id == owner.id,
                EmpresaUsuario.rol == RolEmpresa.OWNER,
            )
            .count()
            == 1
        )
        if not has_owner_role:
            raise RuntimeError(f"Responsable sin rol OWNER para {company_name}")

        for offer_index, offer_spec in enumerate(company_spec.offers):
            existing = find_seed_offer(db, company.id, offer_spec)
            if existing is not None:
                duplicates += 1
                continue
            dto = CreateOfertaDTO(
                empresa_id=company.id,
                titulo=offer_spec.title,
                descripcion=offer_spec.description,
                publicada=True,
                fecha_publicacion=publication_date(company.id, offer_index),
            )
            model = OfertaMapper.to_model(dto)
            db.add(model)
            created.append(model)
    db.flush()

    counts_after = table_counts(db)
    other_rows_after = other_table_fingerprints(db)
    for offer_id, original in existing_before.items():
        current = db.get(Oferta, offer_id)
        current_values = (
            current.empresa_id,
            current.titulo,
            current.descripcion,
            current.publicada,
            current.fecha_publicacion,
        )
        if current_values != original:
            raise RuntimeError(f"Se modifico la oferta preexistente {offer_id}")
    if counts_after["oferta"] != counts_before["oferta"] + len(created):
        raise RuntimeError("El conteo de ofertas no aumento como se esperaba")
    if other_rows_after != other_rows_before:
        raise RuntimeError("Se modificaron datos ajenos a oferta")
    for table_name, count in counts_before.items():
        if table_name != "oferta" and counts_after[table_name] != count:
            raise RuntimeError(f"Cambio inesperado en {table_name}")

    seed_models = []
    for company_name, company_spec in COMPANIES.items():
        company = companies_by_name[company_name]
        for offer_spec in company_spec.offers:
            model = find_seed_offer(db, company.id, offer_spec)
            if model is None:
                raise RuntimeError("No se pudo recuperar una oferta del seed")
            seed_models.append(model)
    checks = sql_verifications(db, [model.id for model in seed_models])
    created_ids = [model.id for model in created]
    db.commit()
    persisted = (
        db.query(Oferta).filter(Oferta.id.in_(created_ids)).count()
        if created_ids
        else 0
    )
    if persisted != len(created):
        raise RuntimeError("No se verificaron todas las ofertas persistidas")
    return {
        "ofertas_creadas": len(created),
        "ofertas_omitidas_por_duplicado": duplicates,
        "ids_creados": created_ids,
        "conteos_antes": counts_before,
        "conteos_despues": counts_after,
        "otras_tablas_sin_cambios": other_rows_after == other_rows_before,
        "ofertas_preexistentes_sin_cambios": True,
        "verificaciones_sql": checks,
        "filas_persistidas_verificadas": persisted,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        try:
            database = assert_safe_database(db)
            companies_by_name, owner_by_company = validate_manifest(db)
            preview = dry_run_report(db, companies_by_name, owner_by_company)
            output: dict[str, object] = {
                "mode": "dry-run" if args.dry_run else "apply",
                "database": database,
                "empresas_existentes": len(companies_by_name),
                "ofertas_existentes": db.query(Oferta).count(),
                "conteos_actuales": table_counts(db),
                "manifest": preview,
            }
            if args.dry_run:
                output["postgresql_modificado"] = False
            else:
                output["resultado"] = apply_seed(
                    db, companies_by_name, owner_by_company
                )
        except Exception:
            db.rollback()
            raise
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

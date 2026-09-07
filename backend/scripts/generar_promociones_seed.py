"""Crea promociones para usuarios que no pertenecen a ninguna empresa.

Uso desde la raiz del repositorio:

    python backend/scripts/generar_promociones_seed.py --dry-run
    python backend/scripts/generar_promociones_seed.py --apply

El seed es transaccional, determinista e idempotente. Solo opera contra la
base local ``Linkedin`` en entorno ``development`` y la unica tabla que puede
crecer es ``promocion``.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import sys
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
from src.db.models.empresa_usuario_model import EmpresaUsuario  # noqa: E402
from src.db.models.promocion_model import Promocion  # noqa: E402
from src.db.models.usuario_model import Usuario  # noqa: E402
from src.dtos.promocion_dto import CreatePromocionDTO  # noqa: E402
from src.mappers.promocion_mapper import PromocionMapper  # noqa: E402
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

REFERENCE_DATE = datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc)

FORBIDDEN_VISIBLE_FRAGMENTS = (
    "dataset",
    "datos generados",
    "base local",
    "perfil de prueba",
    "promoción ficticia",
    "promocion ficticia",
    "usuario de prueba",
    "información simulada",
    "informacion simulada",
)


@dataclass(frozen=True)
class PromotionSpec:
    title: str
    description: str


PROMOTIONS: dict[str, PromotionSpec] = {
    "Agustin Pelachini": PromotionSpec(
        title="Gestión de operaciones de atención al cliente",
        description=(
            "Profesional en gestión de call centers y operaciones BPO, con foco en "
            "calidad de servicio, eficiencia y desarrollo de equipos. Trabajo con "
            "indicadores como CSAT, FCR y AHT para convertir desvíos operativos en "
            "planes de mejora sostenibles.\n\n"
            "Busco liderar operaciones de atención al cliente en Argentina, Córdoba, "
            "donde pueda ordenar procesos, acompañar a los equipos y mejorar la "
            "experiencia de clientes en contextos de alta demanda."
        ),
    ),
    "Benjamin Jerez": PromotionSpec(
        title="Dirección creativa y estrategia de marca",
        description=(
            "Director creativo orientado a construir identidades claras y campañas "
            "capaces de conectar marcas con nuevas audiencias. Combino concepto, "
            "diseño y lectura de resultados para llevar una idea desde el brief hasta "
            "su ejecución en distintos canales.\n\n"
            "Estoy interesado en desafíos de dirección creativa, branding y campañas "
            "de consumo masivo, con base en Argentina, Mendoza y apertura a colaborar "
            "con equipos multidisciplinarios."
        ),
    ),
    "Fernando Mayer": PromotionSpec(
        title="Ingeniería electrónica y automatización industrial",
        description=(
            "Ingeniero electrónico interesado en el diseño, la integración y la puesta "
            "en marcha de soluciones para entornos industriales. Me motiva trabajar "
            "sobre control, instrumentación y sistemas que mejoren la confiabilidad de "
            "los procesos.\n\n"
            "Busco una oportunidad inicial o de desarrollo profesional en Argentina, "
            "Rosario, dentro de equipos de automatización, electrónica aplicada o "
            "mantenimiento de tecnología industrial."
        ),
    ),
    "Franco Bosseti": PromotionSpec(
        title="Masoterapia y bienestar corporal",
        description=(
            "Masajista profesional enfocado en brindar sesiones personalizadas de "
            "relajación, recuperación muscular y bienestar corporal. Priorizo la "
            "escucha, el trato respetuoso y la adaptación de cada técnica a las "
            "necesidades de la persona.\n\n"
            "Me interesa integrarme a un centro de bienestar, espacio deportivo o "
            "equipo interdisciplinario en Argentina, Mar del Plata, donde pueda aportar "
            "una atención responsable y cercana."
        ),
    ),
    "Franco Ghirardi": PromotionSpec(
        title="Dirección financiera y planificación estratégica",
        description=(
            "Profesional de finanzas con experiencia en planificación, liquidez, riesgo "
            "y seguimiento de desempeño. Aporto una mirada que conecta los indicadores "
            "financieros con las decisiones comerciales y operativas del negocio.\n\n"
            "Busco posiciones de liderazgo financiero en Argentina, Buenos Aires, con "
            "responsabilidad sobre estrategia, presupuesto y construcción de equipos "
            "orientados a decisiones basadas en datos."
        ),
    ),
    "Gael Ponce": PromotionSpec(
        title="Ingeniería de inteligencia artificial aplicada",
        description=(
            "Ingeniero especializado en inteligencia artificial, automatización y "
            "desarrollo de soluciones basadas en datos. Me interesa transformar "
            "problemas concretos en sistemas medibles, mantenibles y útiles para las "
            "personas que los utilizan.\n\n"
            "Estoy buscando proyectos de machine learning, IA generativa o ingeniería "
            "de datos en Argentina, Córdoba, especialmente en equipos que valoren la "
            "experimentación rigurosa y la calidad del producto."
        ),
    ),
    "Ighnas Al-Mutto": PromotionSpec(
        title="Gestión financiera para energía e industria",
        description=(
            "Ejecutivo financiero orientado a planificación, control de gestión y "
            "evaluación de inversiones en organizaciones industriales. Mi enfoque "
            "integra disciplina de capital, análisis de escenarios y acompañamiento a "
            "las áreas operativas.\n\n"
            "Me interesan responsabilidades de CFO o dirección financiera en energía, "
            "infraestructura e industria, con base en Emiratos Árabes Unidos, Abu Dabi "
            "y alcance regional."
        ),
    ),
    "Ignacio Libermann": PromotionSpec(
        title="Dirección de servicios veterinarios felinos",
        description=(
            "Profesional dedicado a la gestión de servicios veterinarios especializados "
            "en salud felina y rescate. Puedo aportar coordinación de equipos, "
            "organización de insumos y procesos de atención centrados en el bienestar "
            "animal.\n\n"
            "Busco participar en la dirección o expansión de clínicas y organizaciones "
            "de cuidado animal en Argentina, Santa Fe, combinando sostenibilidad "
            "operativa con una atención de calidad."
        ),
    ),
    "Juan Cruz Maletti": PromotionSpec(
        title="Ingeniería mecánica y desarrollo de producto",
        description=(
            "Ingeniero mecánico orientado al diseño de componentes, análisis técnico y "
            "optimización de procesos industriales. Disfruto convertir requerimientos "
            "complejos en soluciones fabricables, confiables y bien documentadas.\n\n"
            "Busco sumarme a proyectos de diseño mecánico, desarrollo de producto o "
            "mejora continua en Argentina, Buenos Aires, con espacio para colaborar "
            "entre ingeniería, producción y calidad."
        ),
    ),
    "Juan Cruz Moyano": PromotionSpec(
        title="Dirección ejecutiva en industria alimentaria",
        description=(
            "Ejecutivo con foco en estrategia, crecimiento y coordinación de equipos "
            "dentro de la industria alimentaria. Trabajo para traducir objetivos de "
            "largo plazo en prioridades operativas y comerciales que puedan medirse y "
            "sostenerse.\n\n"
            "Estoy abierto a posiciones de dirección general, desarrollo de negocios u "
            "operaciones en Argentina, Rosario, dentro de compañías que busquen escalar "
            "con una gestión ordenada."
        ),
    ),
    "Lorenzo Diaz": PromotionSpec(
        title="Desarrollo de negocios en telecomunicaciones",
        description=(
            "Empresario del sector de telecomunicaciones con interés en infraestructura, "
            "conectividad y crecimiento de servicios digitales. Aporto visión comercial "
            "y capacidad para evaluar iniciativas que requieren coordinación técnica, "
            "financiera y regulatoria.\n\n"
            "Busco liderar o acompañar proyectos de expansión de redes y nuevos negocios "
            "en Argentina, Mendoza, junto a equipos que quieran ampliar el acceso a "
            "soluciones de conectividad."
        ),
    ),
    "Lucas Estevo": PromotionSpec(
        title="Asesoramiento comercial automotor",
        description=(
            "Profesional comercial del sector automotor, enfocado en acompañar a cada "
            "cliente desde la elección del vehículo hasta la entrega y la posventa. Me "
            "destaco por la escucha, la explicación clara de alternativas y el "
            "seguimiento responsable.\n\n"
            "Me interesa crecer en ventas, experiencia del cliente o gestión comercial "
            "de concesionarias en Argentina, Neuquén, aportando una atención transparente "
            "y orientada a relaciones de largo plazo."
        ),
    ),
    "Manuel Valle": PromotionSpec(
        title="Dirección y transformación de pymes",
        description=(
            "Profesional dedicado a ordenar y fortalecer pequeñas y medianas empresas. "
            "Trabajo sobre estrategia, procesos, flujo de caja y desarrollo comercial "
            "para que el crecimiento no dependa solamente de la operación cotidiana.\n\n"
            "Busco colaborar en roles de dirección, consultoría o transformación "
            "empresarial en Argentina, Salta, con organizaciones que necesiten convertir "
            "sus objetivos en una estructura de gestión concreta."
        ),
    ),
}


def promotion_date(usuario_id: int) -> datetime:
    """Entrega fechas UTC estables, ligeramente distribuidas y anteriores al seed."""
    return REFERENCE_DATE - timedelta(
        hours=(usuario_id * 5) % 36,
        minutes=(usuario_id * 11) % 60,
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
        if table_name == "promocion":
            continue
        digest = hashlib.sha256()
        rows = db.execute(
            text(
                f'SELECT row_to_json(item)::text FROM public."{table_name}" AS item '
                "ORDER BY row_to_json(item)::text"
            )
        ).scalars()
        for row in rows:
            digest.update(row.encode("utf-8"))
            digest.update(b"\n")
        result[table_name] = digest.hexdigest()
    return result


def existing_promotion_snapshot(db) -> dict[int, tuple[object, ...]]:
    return {
        item.id: (
            item.usuario_id,
            item.titulo,
            item.descripcion,
            item.fecha_creacion,
        )
        for item in db.query(Promocion).order_by(Promocion.id)
    }


def membership_details(db, usuario_id: int) -> list[dict[str, object]]:
    rows = (
        db.query(EmpresaUsuario, Empresa)
        .join(Empresa, Empresa.id == EmpresaUsuario.empresa_id)
        .filter(EmpresaUsuario.usuario_id == usuario_id)
        .order_by(Empresa.id)
        .all()
    )
    return [
        {
            "empresa_id": membership.empresa_id,
            "empresa": company.nombre,
            "rol": membership.rol.value,
        }
        for membership, company in rows
    ]


def validate_manifest(db) -> tuple[list[Usuario], dict[int, list[Promocion]]]:
    users = db.query(Usuario).order_by(Usuario.id).all()
    names = [user.nombre for user in users]
    if len(names) != len(set(names)):
        raise RuntimeError("Hay nombres de usuario duplicados y el matching es ambiguo")

    promotions_by_user = {
        user.id: (
            db.query(Promocion)
            .filter(Promocion.usuario_id == user.id)
            .order_by(Promocion.fecha_creacion.desc(), Promocion.id.desc())
            .all()
        )
        for user in users
    }
    eligible = [
        user
        for user in users
        if not membership_details(db, user.id)
    ]
    eligible_names = {user.nombre for user in eligible}
    if eligible_names != set(PROMOTIONS):
        missing = sorted(eligible_names - set(PROMOTIONS))
        stale = sorted(set(PROMOTIONS) - eligible_names)
        raise RuntimeError(
            "El manifiesto no coincide con los usuarios sin empresa; "
            f"sin definición={missing}, ya no elegibles={stale}"
        )

    now = utc_now()
    for user in eligible:
        if not user.headline or not user.headline.strip():
            raise RuntimeError(f"{user.nombre} no tiene headline")
        if not user.ciudad or ", " not in user.ciudad.strip():
            raise RuntimeError(f"{user.nombre} no tiene ubicación País, Ciudad")
        spec = PROMOTIONS[user.nombre]
        dto = CreatePromocionDTO(
            titulo=spec.title,
            descripcion=spec.description,
        )
        visible = f"{dto.titulo}\n{dto.descripcion}".casefold()
        if any(fragment in visible for fragment in FORBIDDEN_VISIBLE_FRAGMENTS):
            raise RuntimeError(f"Texto técnico visible detectado para {user.nombre}")
        date = promotion_date(user.id)
        if date.utcoffset() is None or date > now:
            raise RuntimeError(f"Fecha inválida para {user.nombre}")
    return users, promotions_by_user


def dry_run_report(
    db,
    users: list[Usuario],
    promotions_by_user: dict[int, list[Promocion]],
) -> dict[str, object]:
    report = []
    ready = existing = members = 0
    for user in sorted(users, key=lambda item: (item.nombre.casefold(), item.id)):
        memberships = membership_details(db, user.id)
        current_promotions = promotions_by_user[user.id]
        item: dict[str, object] = {
            "usuario_id": user.id,
            "usuario": user.nombre,
            "headline": user.headline,
            "ubicacion": user.ciudad,
            "memberships": memberships,
            "promociones_existentes": [promotion.id for promotion in current_promotions],
        }
        if memberships:
            members += 1
            item["estado"] = "omitido_pertenece_a_empresa"
        elif current_promotions:
            existing += 1
            item["estado"] = "omitido_ya_tiene_promocion"
            item["promocion"] = {
                "titulo": current_promotions[0].titulo,
                "descripcion": current_promotions[0].descripcion,
                "fecha_creacion": current_promotions[0].fecha_creacion.isoformat(),
            }
        else:
            ready += 1
            spec = PROMOTIONS[user.nombre]
            item["estado"] = "lista_para_insertar"
            item["promocion"] = {
                "titulo": spec.title,
                "descripcion": spec.description,
                "fecha_creacion": promotion_date(user.id).isoformat(),
            }
        report.append(item)
    return {
        "usuarios": report,
        "total_usuarios": len(users),
        "usuarios_con_empresa": members,
        "usuarios_sin_empresa": len(users) - members,
        "sin_empresa_con_promocion_existente": existing,
        "promociones_listas_para_insertar": ready,
    }


def sql_verifications(db, created_ids: list[int]) -> dict[str, object]:
    values = {
        "usuarios": db.execute(text("SELECT count(*) FROM usuario")).scalar_one(),
        "usuarios_con_empresa": db.execute(
            text(
                "SELECT count(*) FROM usuario u WHERE EXISTS "
                "(SELECT 1 FROM empresa_usuario eu WHERE eu.usuario_id=u.id)"
            )
        ).scalar_one(),
        "usuarios_sin_empresa": db.execute(
            text(
                "SELECT count(*) FROM usuario u WHERE NOT EXISTS "
                "(SELECT 1 FROM empresa_usuario eu WHERE eu.usuario_id=u.id)"
            )
        ).scalar_one(),
        "sin_empresa_sin_promocion": db.execute(
            text(
                "SELECT count(*) FROM usuario u WHERE NOT EXISTS "
                "(SELECT 1 FROM empresa_usuario eu WHERE eu.usuario_id=u.id) "
                "AND NOT EXISTS (SELECT 1 FROM promocion p WHERE p.usuario_id=u.id)"
            )
        ).scalar_one(),
        "promociones": db.execute(text("SELECT count(*) FROM promocion")).scalar_one(),
        "promociones_huerfanas": db.execute(
            text(
                "SELECT count(*) FROM promocion p LEFT JOIN usuario u ON u.id=p.usuario_id "
                "WHERE u.id IS NULL"
            )
        ).scalar_one(),
        "promociones_whitespace": db.execute(
            text(
                "SELECT count(*) FROM promocion "
                "WHERE titulo !~ '[^[:space:]]' OR descripcion !~ '[^[:space:]]'"
            )
        ).scalar_one(),
        "promociones_futuras": db.execute(
            text("SELECT count(*) FROM promocion WHERE fecha_creacion>now()")
        ).scalar_one(),
        "nuevas_con_membership": db.execute(
            text(
                "SELECT count(*) FROM promocion p WHERE p.id=ANY(:ids) AND EXISTS "
                "(SELECT 1 FROM empresa_usuario eu WHERE eu.usuario_id=p.usuario_id)"
            ),
            {"ids": created_ids},
        ).scalar_one(),
        "nuevas_persistidas": db.execute(
            text("SELECT count(*) FROM promocion WHERE id=ANY(:ids)"),
            {"ids": created_ids},
        ).scalar_one(),
        "solicitudes_contratacion": db.execute(
            text("SELECT count(*) FROM solicitud_contratacion_promocion")
        ).scalar_one(),
        "tipo_fecha_creacion": db.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='promocion' "
                "AND column_name='fecha_creacion'"
            )
        ).scalar_one(),
    }
    required_zero = (
        "sin_empresa_sin_promocion",
        "promociones_huerfanas",
        "promociones_whitespace",
        "promociones_futuras",
        "nuevas_con_membership",
    )
    if any(values[key] for key in required_zero):
        raise RuntimeError(f"Falló una verificación SQL: {values}")
    if values["nuevas_persistidas"] != len(created_ids):
        raise RuntimeError("No se localizaron todas las promociones nuevas")
    if values["tipo_fecha_creacion"] != "timestamp with time zone":
        raise RuntimeError("promocion.fecha_creacion no es TIMESTAMPTZ")
    return values


def apply_seed(
    db,
    users: list[Usuario],
    promotions_by_user: dict[int, list[Promocion]],
) -> dict[str, object]:
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('atanes:promociones-seed'))"))
    assert_safe_database(db)
    counts_before = table_counts(db)
    protected_before = other_table_fingerprints(db)
    existing_before = existing_promotion_snapshot(db)
    member_promotion_counts_before = {
        user.id: len(promotions_by_user[user.id])
        for user in users
        if membership_details(db, user.id)
    }

    created: list[Promocion] = []
    skipped_existing = 0
    skipped_membership = 0
    for user in users:
        memberships = membership_details(db, user.id)
        if memberships:
            skipped_membership += 1
            continue
        current = (
            db.query(Promocion)
            .filter(Promocion.usuario_id == user.id)
            .order_by(Promocion.id)
            .all()
        )
        if current:
            skipped_existing += 1
            continue

        spec = PROMOTIONS[user.nombre]
        dto = CreatePromocionDTO(
            titulo=spec.title,
            descripcion=spec.description,
        )
        model = PromocionMapper.to_model(dto, user.id)
        model.fecha_creacion = promotion_date(user.id)
        db.add(model)
        created.append(model)

    db.flush()
    created_ids = [model.id for model in created]

    for user in users:
        if membership_details(db, user.id):
            current_count = (
                db.query(Promocion).filter(Promocion.usuario_id == user.id).count()
            )
            if current_count != member_promotion_counts_before[user.id]:
                raise RuntimeError(f"Se agregó una promoción al miembro {user.nombre}")
    for promotion_id, original in existing_before.items():
        current = db.get(Promocion, promotion_id)
        values = (
            current.usuario_id,
            current.titulo,
            current.descripcion,
            current.fecha_creacion,
        )
        if values != original:
            raise RuntimeError(f"Se modificó la promoción preexistente {promotion_id}")

    counts_after = table_counts(db)
    protected_after = other_table_fingerprints(db)
    if counts_after["promocion"] != counts_before["promocion"] + len(created):
        raise RuntimeError("El conteo de promociones no aumentó como se esperaba")
    if protected_after != protected_before:
        raise RuntimeError("Se modificaron filas ajenas a promocion")
    for table_name, count in counts_before.items():
        if table_name != "promocion" and counts_after[table_name] != count:
            raise RuntimeError(f"Cambio inesperado en {table_name}")

    checks = sql_verifications(db, created_ids)
    db.commit()

    persisted = (
        db.query(Promocion).filter(Promocion.id.in_(created_ids)).count()
        if created_ids
        else 0
    )
    if persisted != len(created_ids):
        raise RuntimeError("No se verificaron todas las promociones persistidas")
    return {
        "promociones_creadas": len(created),
        "omitidos_por_promocion_existente": skipped_existing,
        "omitidos_por_membership": skipped_membership,
        "ids_creados": created_ids,
        "conteos_antes": counts_before,
        "conteos_despues": counts_after,
        "otras_tablas_sin_cambios": protected_after == protected_before,
        "promociones_preexistentes_sin_cambios": True,
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
            users, promotions_by_user = validate_manifest(db)
            preview = dry_run_report(db, users, promotions_by_user)
            output: dict[str, object] = {
                "mode": "dry-run" if args.dry_run else "apply",
                "database": database,
                "conteos_actuales": table_counts(db),
                "manifest": preview,
            }
            if args.dry_run:
                output["postgresql_modificado"] = False
            else:
                output["resultado"] = apply_seed(db, users, promotions_by_user)
        except Exception:
            db.rollback()
            raise
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

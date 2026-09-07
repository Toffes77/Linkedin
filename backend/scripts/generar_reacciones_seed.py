"""Agrega reacciones deterministas a las publicaciones existentes de Atanes.

Uso desde la raiz del repositorio:

    python backend/scripts/generar_reacciones_seed.py --dry-run
    python backend/scripts/generar_reacciones_seed.py --apply

El seed es transaccional e idempotente. Solo opera contra la base local
``Linkedin`` en entorno ``development`` y nunca crea autorreacciones.
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
from pathlib import Path
from urllib.parse import urlparse


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

import src.app  # noqa: E402,F401 - registra todos los modelos relacionados
from sqlalchemy import text  # noqa: E402

from src.db.connection import SessionLocal  # noqa: E402
from src.db.models.publicacion_model import Publicacion  # noqa: E402
from src.db.models.reaciones_model import Reacciones  # noqa: E402
from src.db.models.usuario_model import Usuario  # noqa: E402
from src.dtos.reacciones_dto import CreateReaccionDTO  # noqa: E402
from src.mappers.reaccion_mapper import ReaccionMapper  # noqa: E402


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

VALID_TYPES = ("like", "celebrar", "apoyar", "interesante")


@dataclass(frozen=True)
class PostRule:
    author: str
    reaction_count: int
    category: str


@dataclass(frozen=True)
class PlannedReaction:
    usuario_id: int
    usuario_nombre: str
    publicacion_id: int
    tipo: str


# El conteo y la categoría fueron definidos después de leer las 25
# publicaciones actuales. La selección de usuarios se hace de forma estable.
POST_RULES: dict[int, PostRule] = {
    1: PostRule("Santín Ben-Konka", 4, "technical"),
    2: PostRule("Ignacio Labonia", 3, "technical"),
    3: PostRule("Joaquin Gambeta", 0, "support"),
    4: PostRule("Binyamin Al-Ghomiz", 4, "technical"),
    5: PostRule("Luca Di Lauro", 3, "business"),
    6: PostRule("Jacques-Antoine Lacroix", 8, "celebration"),
    7: PostRule("Alexandre Bompard", 6, "celebration"),
    8: PostRule("Manfred Paulmann", 7, "support"),
    9: PostRule("Andy Jassy", 8, "technical"),
    10: PostRule("Henrique Braun", 5, "support"),
    11: PostRule("Agustin Pelachini", 5, "support"),
    12: PostRule("Benjamin Jerez", 7, "business"),
    13: PostRule("Binyamin Al-Ghomiz", 6, "technical"),
    14: PostRule("Ignacio Libermann", 4, "support"),
    15: PostRule("Joaquin Gambeta", 3, "support"),
    16: PostRule("Juan Cruz Maletti", 5, "technical"),
    17: PostRule("Juan Cruz Moyano", 4, "business"),
    18: PostRule("Lorenzo Diaz", 5, "technical"),
    19: PostRule("Luca Di Lauro", 1, "business"),
    20: PostRule("Lucas Estevo", 3, "business"),
    21: PostRule("Manuel Valle", 4, "business"),
    22: PostRule("Santín Ben-Konka", 5, "technical"),
    23: PostRule("Fernando Mayer", 9, "celebration"),
    24: PostRule("Franco Ghirardi", 6, "technical"),
    25: PostRule("Gael Ponce", 8, "technical"),
}

TYPE_PATTERNS = {
    "technical": (
        "interesante",
        "like",
        "interesante",
        "like",
        "apoyar",
        "celebrar",
    ),
    "celebration": (
        "celebrar",
        "like",
        "celebrar",
        "apoyar",
        "like",
        "interesante",
    ),
    "support": (
        "apoyar",
        "like",
        "apoyar",
        "interesante",
        "celebrar",
        "like",
    ),
    "business": (
        "like",
        "interesante",
        "like",
        "celebrar",
        "apoyar",
        "interesante",
    ),
}


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


def protected_fingerprints(db) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for table_name in DOMAIN_TABLES:
        if table_name == "reacciones":
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
        fingerprints[table_name] = digest.hexdigest()
    return fingerprints


def reaction_snapshot(db) -> dict[tuple[int, int], str]:
    return {
        (reaction.usuario_id, reaction.publicacion_id): reaction.tipo
        for reaction in db.query(Reacciones).all()
    }


def validate_current_state(db) -> tuple[list[Usuario], list[Publicacion]]:
    users = db.query(Usuario).order_by(Usuario.id).all()
    posts = db.query(Publicacion).order_by(Publicacion.id).all()
    users_by_id = {user.id: user for user in users}

    if len(users_by_id) != len(users):
        raise RuntimeError("Hay IDs de usuario duplicados")
    if set(post.id for post in posts) != set(POST_RULES):
        raise RuntimeError(
            "Las publicaciones actuales no coinciden con el manifiesto del seed"
        )
    for post in posts:
        rule = POST_RULES[post.id]
        if post.autor_id not in users_by_id:
            raise RuntimeError(f"La publicación {post.id} tiene un autor inexistente")
        if users_by_id[post.autor_id].nombre != rule.author:
            raise RuntimeError(
                f"El autor de la publicación {post.id} no coincide con el manifiesto"
            )
        if not 0 <= rule.reaction_count < len(users):
            raise RuntimeError(f"Cantidad inválida para la publicación {post.id}")
        if rule.category not in TYPE_PATTERNS:
            raise RuntimeError(f"Categoría inválida para la publicación {post.id}")

    existing_self_reactions = db.execute(
        text(
            "SELECT count(*) FROM reacciones r JOIN publicacion p "
            "ON p.id=r.publicacion_id WHERE r.usuario_id=p.autor_id"
        )
    ).scalar_one()
    if existing_self_reactions:
        raise RuntimeError("Ya existen autorreacciones; el seed no las eliminará")
    return users, posts


def stable_user_score(publicacion_id: int, user: Usuario) -> bytes:
    value = (
        f"atanes-reacciones-v1:{publicacion_id}:{user.id}:{user.nombre}"
    ).encode("utf-8")
    return hashlib.sha256(value).digest()


def build_plan(
    users: list[Usuario],
    posts: list[Publicacion],
) -> dict[int, list[PlannedReaction]]:
    plan: dict[int, list[PlannedReaction]] = {}
    seen_pairs: set[tuple[int, int]] = set()
    for post in posts:
        rule = POST_RULES[post.id]
        eligible = [user for user in users if user.id != post.autor_id]
        eligible.sort(key=lambda user: (stable_user_score(post.id, user), user.id))
        selected = eligible[: rule.reaction_count]
        pattern = TYPE_PATTERNS[rule.category]
        post_plan = []
        for index, user in enumerate(selected):
            reaction_type = pattern[index % len(pattern)]
            pair = (user.id, post.id)
            if pair in seen_pairs:
                raise RuntimeError(f"Par duplicado generado: {pair}")
            seen_pairs.add(pair)
            dto = CreateReaccionDTO(
                usuario_id=user.id,
                publicacion_id=post.id,
                tipo=reaction_type,
            )
            if dto.usuario_id == post.autor_id:
                raise RuntimeError(f"Autorreacción generada para publicación {post.id}")
            if dto.tipo not in VALID_TYPES:
                raise RuntimeError(f"Tipo inválido generado: {dto.tipo}")
            post_plan.append(
                PlannedReaction(
                    usuario_id=user.id,
                    usuario_nombre=user.nombre,
                    publicacion_id=post.id,
                    tipo=dto.tipo,
                )
            )
        plan[post.id] = post_plan
    return plan


def dry_run_report(
    db,
    posts: list[Publicacion],
    plan: dict[int, list[PlannedReaction]],
) -> dict[str, object]:
    existing = reaction_snapshot(db)
    ready = skipped = 0
    report = []
    for post in posts:
        reactions = []
        for planned in plan[post.id]:
            current_type = existing.get((planned.usuario_id, post.id))
            if current_type is None:
                ready += 1
                status = "lista_para_insertar"
            else:
                skipped += 1
                status = "omitida_reaccion_existente"
            reactions.append(
                {
                    "usuario_id": planned.usuario_id,
                    "usuario": planned.usuario_nombre,
                    "tipo_planeado": planned.tipo,
                    "tipo_existente": current_type,
                    "estado": status,
                }
            )
        report.append(
            {
                "publicacion_id": post.id,
                "autor": post.autor.nombre,
                "resumen": " ".join(post.texto.split())[:140],
                "reacciones_objetivo": len(plan[post.id]),
                "reacciones": reactions,
            }
        )
    planned_types = Counter(
        reaction.tipo for reactions in plan.values() for reaction in reactions
    )
    target_distribution = Counter(len(reactions) for reactions in plan.values())
    return {
        "publicaciones": report,
        "reacciones_definidas": sum(len(items) for items in plan.values()),
        "reacciones_listas_para_insertar": ready,
        "reacciones_omitidas_existentes": skipped,
        "distribucion_planeada_por_tipo": dict(sorted(planned_types.items())),
        "distribucion_publicaciones_por_cantidad": {
            str(count): amount for count, amount in sorted(target_distribution.items())
        },
    }


def sql_verifications(db) -> dict[str, object]:
    totals_by_type = {
        row.tipo: row.cantidad
        for row in db.execute(
            text(
                "SELECT tipo, count(*) cantidad FROM reacciones "
                "GROUP BY tipo ORDER BY tipo"
            )
        ).mappings()
    }
    per_post = [
        dict(row)
        for row in db.execute(
            text(
                "SELECT p.id publicacion_id, u.nombre autor, count(r.usuario_id) reacciones "
                "FROM publicacion p JOIN usuario u ON u.id=p.autor_id "
                "LEFT JOIN reacciones r ON r.publicacion_id=p.id "
                "GROUP BY p.id,u.nombre ORDER BY p.id"
            )
        ).mappings()
    ]
    per_user = [
        dict(row)
        for row in db.execute(
            text(
                "SELECT u.id usuario_id,u.nombre,count(r.publicacion_id) reacciones "
                "FROM usuario u LEFT JOIN reacciones r ON r.usuario_id=u.id "
                "GROUP BY u.id,u.nombre ORDER BY lower(u.nombre),u.id"
            )
        ).mappings()
    ]
    checks = {
        "total_reacciones": db.execute(
            text("SELECT count(*) FROM reacciones")
        ).scalar_one(),
        "autorreacciones": db.execute(
            text(
                "SELECT count(*) FROM reacciones r JOIN publicacion p "
                "ON p.id=r.publicacion_id WHERE r.usuario_id=p.autor_id"
            )
        ).scalar_one(),
        "pares_duplicados": db.execute(
            text(
                "SELECT count(*) FROM (SELECT usuario_id,publicacion_id "
                "FROM reacciones GROUP BY usuario_id,publicacion_id "
                "HAVING count(*)>1) duplicated"
            )
        ).scalar_one(),
        "tipos_invalidos": db.execute(
            text(
                "SELECT count(*) FROM reacciones WHERE tipo NOT IN "
                "('like','celebrar','apoyar','interesante')"
            )
        ).scalar_one(),
        "usuarios_huerfanos": db.execute(
            text(
                "SELECT count(*) FROM reacciones r LEFT JOIN usuario u "
                "ON u.id=r.usuario_id WHERE u.id IS NULL"
            )
        ).scalar_one(),
        "publicaciones_huerfanas": db.execute(
            text(
                "SELECT count(*) FROM reacciones r LEFT JOIN publicacion p "
                "ON p.id=r.publicacion_id WHERE p.id IS NULL"
            )
        ).scalar_one(),
        "publicaciones_sin_reacciones": sum(
            row["reacciones"] == 0 for row in per_post
        ),
        "publicaciones_con_reacciones": sum(
            row["reacciones"] > 0 for row in per_post
        ),
        "distribucion_por_tipo": totals_by_type,
        "reacciones_por_publicacion": per_post,
        "reacciones_por_usuario": per_user,
    }
    zero_checks = (
        "autorreacciones",
        "pares_duplicados",
        "tipos_invalidos",
        "usuarios_huerfanos",
        "publicaciones_huerfanas",
    )
    if any(checks[key] for key in zero_checks):
        raise RuntimeError(f"Falló una verificación SQL: {checks}")
    if checks["publicaciones_sin_reacciones"] < 1:
        raise RuntimeError("La distribución no dejó publicaciones sin reacciones")
    if set(totals_by_type) != set(VALID_TYPES):
        raise RuntimeError("No están representados todos los tipos de reacción")
    return checks


def apply_seed(
    db,
    posts: list[Publicacion],
    plan: dict[int, list[PlannedReaction]],
) -> dict[str, object]:
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('atanes:reacciones-seed'))"))
    assert_safe_database(db)
    counts_before = table_counts(db)
    protected_before = protected_fingerprints(db)
    existing_before = reaction_snapshot(db)
    created: list[PlannedReaction] = []
    skipped = 0

    for post in posts:
        for planned in plan[post.id]:
            pair = (planned.usuario_id, planned.publicacion_id)
            if db.get(Reacciones, pair) is not None:
                skipped += 1
                continue
            dto = CreateReaccionDTO(
                usuario_id=planned.usuario_id,
                publicacion_id=planned.publicacion_id,
                tipo=planned.tipo,
            )
            db.add(ReaccionMapper.to_model(dto))
            created.append(planned)
    db.flush()

    for pair, previous_type in existing_before.items():
        current = db.get(Reacciones, pair)
        if current is None or current.tipo != previous_type:
            raise RuntimeError(f"Se modificó la reacción preexistente {pair}")

    counts_after = table_counts(db)
    protected_after = protected_fingerprints(db)
    if counts_after["reacciones"] != counts_before["reacciones"] + len(created):
        raise RuntimeError("El conteo de reacciones no aumentó como se esperaba")
    if protected_after != protected_before:
        raise RuntimeError("Se modificaron filas ajenas a reacciones")
    for table_name, count in counts_before.items():
        if table_name != "reacciones" and counts_after[table_name] != count:
            raise RuntimeError(f"Cambio inesperado en {table_name}")

    checks = sql_verifications(db)
    for planned in created:
        current = db.get(
            Reacciones,
            (planned.usuario_id, planned.publicacion_id),
        )
        if current is None or current.tipo != planned.tipo:
            raise RuntimeError("No se pudo verificar una reacción creada")
    db.commit()
    return {
        "reacciones_creadas": len(created),
        "reacciones_omitidas_existentes": skipped,
        "conteos_antes": counts_before,
        "conteos_despues": counts_after,
        "otras_tablas_sin_cambios": protected_after == protected_before,
        "reacciones_preexistentes_sin_cambios": True,
        "verificaciones_sql": checks,
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
            users, posts = validate_current_state(db)
            plan = build_plan(users, posts)
            preview = dry_run_report(db, posts, plan)
            output: dict[str, object] = {
                "mode": "dry-run" if args.dry_run else "apply",
                "database": database,
                "usuarios": len(users),
                "publicaciones": len(posts),
                "reacciones_existentes": db.query(Reacciones).count(),
                "conteos_actuales": table_counts(db),
                "manifest": preview,
            }
            if args.dry_run:
                output["postgresql_modificado"] = False
            else:
                output["resultado"] = apply_seed(db, posts, plan)
        except Exception:
            db.rollback()
            raise
    # ASCII escapado mantiene el JSON transportable también en consolas de
    # Windows configuradas con cp1252; al decodificar conserva todo Unicode.
    print(json.dumps(output, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

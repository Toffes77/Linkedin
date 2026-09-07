"""Importa perfiles, empresas y OWNER desde las carpetas temporales del proyecto.

Uso desde la raiz del repositorio:

    python backend/scripts/importar_datos_temporales.py --dry-run
    python backend/scripts/importar_datos_temporales.py --apply

El modo --apply solo opera contra la base local Linkedin en entorno development y
aborta si alguna tabla de dominio contiene datos.
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
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_DIR = BACKEND_DIR.parent
PROFILE_SOURCE_DIR = REPOSITORY_DIR / "fotos_perfiles_temporal"
COMPANY_SOURCE_DIR = REPOSITORY_DIR / "empresas_perfiles_temporal"
TEMPORARY_PASSWORD = "AtanesTest2026!"
NEUTRAL_CITY = "No especificada"
EMAIL_DOMAIN = "atanes.example.com"
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

from src.dtos.empresa_dto import CreateEmpresaDTO  # noqa: E402
from src.dtos.usuario_dto import CreateUsuarioDTO  # noqa: E402
from src.mappers.empresa_mapper import EmpresaMapper  # noqa: E402
from src.mappers.empresa_usuario_mapper import EmpresaUsuarioMapper  # noqa: E402
from src.mappers.usuario_mapper import UsuarioMapper  # noqa: E402
from src.utils.hash import hash_password  # noqa: E402
from src.utils.image_storage import (  # noqa: E402
    delete_managed_image,
    save_image,
    validate_and_get_extension,
)


@dataclass(frozen=True)
class ProfileCandidate:
    path: Path
    name: str
    headline: str
    width: int
    height: int
    extension: str
    digest: str


@dataclass(frozen=True)
class ProfileSpec:
    identity_key: str
    name: str
    headline: str
    email: str
    selected: ProfileCandidate
    candidates: tuple[ProfileCandidate, ...]


@dataclass(frozen=True)
class CompanySpec:
    identity_key: str
    name: str
    owners: tuple[str, ...]
    owner_text: str
    path: Path
    extension: str
    digest: str


def normalize_identity(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    without_dashes = re.sub(r"[-‐-―]", " ", without_accents)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_dashes.casefold()).split())


def email_slug(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        char for char in decomposed if not unicodedata.combining(char) and ord(char) < 128
    )
    return re.sub(r"[^a-z0-9]+", ".", ascii_value.casefold()).strip(".")


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_filename(path: Path, entity_kind: str) -> tuple[str, str]:
    left, separator, right = path.stem.partition(" - ")
    left = left.strip()
    right = right.strip()
    if not separator or not left or not right:
        raise ValueError(
            f"{entity_kind}: el archivo no respeta '<nombre> - <detalle>': {path.name}"
        )
    return left, right


def image_metadata(path: Path) -> tuple[int, int, str]:
    content = path.read_bytes()
    extension = validate_and_get_extension(path.name, content)
    with Image.open(path) as image:
        return image.width, image.height, extension


def build_profiles() -> tuple[list[ProfileSpec], dict[str, list[str]]]:
    if not PROFILE_SOURCE_DIR.is_dir():
        raise FileNotFoundError(PROFILE_SOURCE_DIR)

    groups: dict[str, list[ProfileCandidate]] = {}
    for path in sorted(PROFILE_SOURCE_DIR.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file():
            continue
        name, headline = split_filename(path, "Perfil")
        width, height, extension = image_metadata(path)
        key = normalize_identity(name)
        if not key:
            raise ValueError(f"Perfil sin identidad utilizable: {path.name}")
        candidate = ProfileCandidate(
            path=path,
            name=name,
            headline=headline,
            width=width,
            height=height,
            extension=extension,
            digest=file_digest(path),
        )
        groups.setdefault(key, []).append(candidate)

    used_emails: set[str] = set()
    profiles: list[ProfileSpec] = []
    duplicate_sources: dict[str, list[str]] = {}
    for key in sorted(groups):
        candidates = tuple(sorted(groups[key], key=lambda item: item.path.name.casefold()))
        selected = max(
            candidates,
            key=lambda item: (min(item.width, item.height), item.width * item.height, item.path.name),
        )
        base = email_slug(selected.name)
        if not base:
            raise ValueError(f"No se pudo generar email para {selected.name}")
        suffix = 1
        email = f"{base}@{EMAIL_DOMAIN}"
        while email in used_emails:
            suffix += 1
            email = f"{base}.{suffix}@{EMAIL_DOMAIN}"
        used_emails.add(email)

        CreateUsuarioDTO(
            email=email,
            password=TEMPORARY_PASSWORD,
            nombre=selected.name,
            headline=selected.headline,
            ciudad=NEUTRAL_CITY,
        )
        profiles.append(
            ProfileSpec(
                identity_key=key,
                name=selected.name,
                headline=selected.headline,
                email=email,
                selected=selected,
                candidates=candidates,
            )
        )
        if len(candidates) > 1:
            duplicate_sources[selected.name] = [candidate.path.name for candidate in candidates]

    if not profiles:
        raise ValueError("No se encontraron perfiles")
    return profiles, duplicate_sources


def owner_partitions(owner_text: str, profile_keys: set[str]) -> list[tuple[str, ...]]:
    target = normalize_identity(owner_text)
    ordered_keys = sorted(profile_keys, key=lambda key: (-len(key.split()), key))

    def visit(remaining: str) -> list[tuple[str, ...]]:
        if not remaining:
            return [()]
        solutions: list[tuple[str, ...]] = []
        for key in ordered_keys:
            if remaining == key:
                solutions.append((key,))
            elif remaining.startswith(f"{key} "):
                solutions.extend((key, *tail) for tail in visit(remaining[len(key) + 1 :]))
        return solutions

    return list(dict.fromkeys(visit(target)))


def build_companies(
    profiles: list[ProfileSpec],
) -> tuple[list[CompanySpec], list[dict[str, object]], list[dict[str, object]]]:
    if not COMPANY_SOURCE_DIR.is_dir():
        raise FileNotFoundError(COMPANY_SOURCE_DIR)

    profiles_by_key = {profile.identity_key: profile for profile in profiles}
    profile_sources_by_hash: dict[str, list[str]] = {}
    for profile in profiles:
        for candidate in profile.candidates:
            profile_sources_by_hash.setdefault(candidate.digest, []).append(candidate.path.name)

    companies: list[CompanySpec] = []
    ignored: list[dict[str, object]] = []
    normalization_notes: list[dict[str, object]] = []
    company_keys: set[str] = set()

    for path in sorted(COMPANY_SOURCE_DIR.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file():
            continue
        digest = file_digest(path)
        if digest in profile_sources_by_hash:
            ignored.append(
                {
                    "file": path.name,
                    "reason": "copia exacta de una foto de perfil, no es un logo",
                    "duplicate_of": profile_sources_by_hash[digest],
                }
            )
            continue

        name, owner_text = split_filename(path, "Empresa")
        _, _, extension = image_metadata(path)
        key = normalize_identity(name)
        if not key or key in company_keys:
            raise ValueError(f"Empresa vacia o duplicada: {path.name}")
        company_keys.add(key)
        CreateEmpresaDTO(nombre=name, industria=None, sitio_web=None)

        partitions = owner_partitions(owner_text, set(profiles_by_key))
        if len(partitions) != 1:
            raise ValueError(
                f"Owners no resolubles de forma inequivoca para {path.name}: {partitions}"
            )
        owners = partitions[0]
        if not owners:
            raise ValueError(f"Empresa sin OWNER: {path.name}")
        if len(set(owners)) != len(owners):
            raise ValueError(f"OWNER repetido en {path.name}")

        for owner_key in owners:
            profile = profiles_by_key[owner_key]
            if owner_text != profile.name or len(owners) > 1:
                normalization_notes.append(
                    {
                        "company": name,
                        "owner_text": owner_text,
                        "matched_profile": profile.name,
                        "normalization": "tildes, mayusculas, guiones o separacion de multiples owners",
                    }
                )

        companies.append(
            CompanySpec(
                identity_key=key,
                name=name,
                owners=owners,
                owner_text=owner_text,
                path=path,
                extension=extension,
                digest=digest,
            )
        )

    if not companies:
        raise ValueError("No se encontraron logos de empresas")
    return companies, ignored, normalization_notes


def build_manifest() -> tuple[dict[str, object], list[ProfileSpec], list[CompanySpec]]:
    profiles, duplicate_sources = build_profiles()
    companies, ignored_company_files, normalization_notes = build_companies(profiles)
    profile_file_count = sum(1 for path in PROFILE_SOURCE_DIR.iterdir() if path.is_file())
    company_file_count = sum(1 for path in COMPANY_SOURCE_DIR.iterdir() if path.is_file())
    profiles_by_key = {profile.identity_key: profile for profile in profiles}

    manifest: dict[str, object] = {
        "profile_file_count": profile_file_count,
        "profile_pattern": "<nombre> - <headline>.<jpg|jpeg|png>",
        "unique_people": len(profiles),
        "profiles": [
            {
                "name": profile.name,
                "headline": profile.headline,
                "email": profile.email,
                "city": NEUTRAL_CITY,
                "selected_photo": profile.selected.path.name,
                "source_variants": [candidate.path.name for candidate in profile.candidates],
            }
            for profile in profiles
        ],
        "duplicate_profile_sources": duplicate_sources,
        "company_file_count": company_file_count,
        "company_pattern": "<empresa> - <owner[, y, + o guion] owner...>.<imagen>",
        "companies_to_create": len(companies),
        "companies": [
            {
                "name": company.name,
                "logo": company.path.name,
                "owner_text": company.owner_text,
                "owners": [profiles_by_key[key].name for key in company.owners],
            }
            for company in companies
        ],
        "ignored_company_files": ignored_company_files,
        "owner_matching_normalizations": normalization_notes,
        "validation": {
            "all_profiles_have_name_and_headline": True,
            "all_companies_have_name": True,
            "all_owners_resolved_uniquely": True,
            "ambiguous_duplicate_entities": False,
            "generated_emails_are_unique": len({profile.email for profile in profiles})
            == len(profiles),
        },
    }
    return manifest, profiles, companies


def assert_safe_database(db) -> dict[str, object]:
    from sqlalchemy import text

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
    if database != "Linkedin" or not ipaddress.ip_interface(server_address).ip.is_loopback:
        raise RuntimeError("Importacion abortada: el servidor efectivo no es Linkedin local")
    return {
        "database": database,
        "server_address": server_address,
        "server_port": server_port,
        "environment": settings.ENVIRONMENT,
    }


def assert_empty_database(db) -> dict[str, int]:
    from sqlalchemy import text

    counts = {
        table: db.execute(text(f'SELECT count(*) FROM public."{table}"')).scalar_one()
        for table in DOMAIN_TABLES
    }
    populated = {table: count for table, count in counts.items() if count}
    if populated:
        raise RuntimeError(
            "Importacion abortada para evitar duplicados; hay tablas con datos: "
            + json.dumps(populated, ensure_ascii=False)
        )
    return counts


def apply_manifest(
    profiles: list[ProfileSpec], companies: list[CompanySpec]
) -> dict[str, object]:
    # Cargar todos los routers registra los modelos relacionados en SQLAlchemy.
    import src.app  # noqa: F401
    from src.db.connection import SessionLocal
    from src.db.models.empresa_usuario_model import RolEmpresa

    created_images: list[tuple[str, str, int]] = []
    with SessionLocal() as db:
        try:
            database = assert_safe_database(db)
            initial_counts = assert_empty_database(db)

            users_by_key = {}
            for profile in profiles:
                dto = CreateUsuarioDTO(
                    email=profile.email,
                    password=TEMPORARY_PASSWORD,
                    nombre=profile.name,
                    headline=profile.headline,
                    ciudad=NEUTRAL_CITY,
                )
                user = UsuarioMapper.to_model(dto, hash_password(dto.password))
                db.add(user)
                users_by_key[profile.identity_key] = user
            db.flush()

            for profile in profiles:
                user = users_by_key[profile.identity_key]
                image_url = save_image(
                    "usuario",
                    user.id,
                    profile.selected.extension,
                    profile.selected.path.read_bytes(),
                )
                created_images.append((image_url, "usuario", user.id))
                user.foto_perfil_url = image_url

            companies_by_key = {}
            for company in companies:
                dto = CreateEmpresaDTO(nombre=company.name, industria=None, sitio_web=None)
                model = EmpresaMapper.to_model(dto)
                db.add(model)
                companies_by_key[company.identity_key] = model
            db.flush()

            for company in companies:
                model = companies_by_key[company.identity_key]
                image_url = save_image(
                    "empresa",
                    model.id,
                    company.extension,
                    company.path.read_bytes(),
                )
                created_images.append((image_url, "empresa", model.id))
                model.foto_perfil_url = image_url
                for owner_key in company.owners:
                    db.add(
                        EmpresaUsuarioMapper.to_model_from_values(
                            empresa_id=model.id,
                            usuario_id=users_by_key[owner_key].id,
                            rol=RolEmpresa.OWNER,
                        )
                    )

            db.flush()
            result = {
                "database": database,
                "initial_counts": initial_counts,
                "users": [
                    {
                        "id": users_by_key[profile.identity_key].id,
                        "name": profile.name,
                        "email": profile.email,
                        "photo_url": users_by_key[profile.identity_key].foto_perfil_url,
                    }
                    for profile in profiles
                ],
                "companies": [
                    {
                        "id": companies_by_key[company.identity_key].id,
                        "name": company.name,
                        "logo_url": companies_by_key[company.identity_key].foto_perfil_url,
                        "owners": [users_by_key[key].nombre for key in company.owners],
                    }
                    for company in companies
                ],
            }
            db.commit()
            return result
        except Exception:
            db.rollback()
            for image_url, entity_type, entity_id in reversed(created_images):
                delete_managed_image(image_url, entity_type, entity_id)
            raise


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    manifest, profiles, companies = build_manifest()
    output: dict[str, object] = {"manifest": manifest}
    if args.apply:
        output["import"] = apply_manifest(profiles, companies)
    else:
        output["mode"] = "dry-run; PostgreSQL no fue modificado"
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

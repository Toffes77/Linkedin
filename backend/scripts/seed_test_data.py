from datetime import date, datetime, timedelta

from sqlalchemy import and_, or_

from src.db.connection import SessionLocal
from src.db.models.conexiones_model import Conexion
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.experiencia_model import Experiencia
from src.db.models.oferta_model import Oferta
from src.db.models.postulacion_model import Postulacion
from src.db.models.publicacion_model import Publicacion
from src.db.models.reaciones_model import Reacciones
from src.db.models.usuario_model import Usuario
from src.utils.hash import hash_password


PASSWORD = "Test1234!"

USUARIOS = [
    {
        "email": "juan.perez@test.com",
        "nombre": "Juan Pérez",
        "headline": "Desarrollador Backend especializado en Python",
        "ciudad": "Buenos Aires",
    },
    {
        "email": "franco.gomez@test.com",
        "nombre": "Franco Gómez",
        "headline": "Ingeniero de Software y líder técnico",
        "ciudad": "Córdoba",
    },
    {
        "email": "pedro.rodriguez@test.com",
        "nombre": "Pedro Rodríguez",
        "headline": "Analista de Datos con foco en producto",
        "ciudad": "Rosario",
    },
    {
        "email": "lucas.fernandez@test.com",
        "nombre": "Lucas Fernández",
        "headline": "Desarrollador Frontend especializado en React",
        "ciudad": "Mendoza",
    },
    {
        "email": "martin.lopez@test.com",
        "nombre": "Martín López",
        "headline": "Project Manager para equipos digitales",
        "ciudad": "La Plata",
    },
]

EMPRESAS = [
    {
        "nombre": "Tech Solutions",
        "industria": "Tecnología",
        "sitio_web": "https://techsolutions.test",
    },
    {
        "nombre": "Globant Test",
        "industria": "Software",
        "sitio_web": "https://globant-test.test",
    },
    {
        "nombre": "Mercado Digital",
        "industria": "Comercio electrónico",
        "sitio_web": "https://mercadodigital.test",
    },
]


def get_or_create_usuario(db, data, creados, omitidos):
    usuario = db.query(Usuario).filter(Usuario.email == data["email"]).first()
    if usuario is not None:
        omitidos.append(f"Usuario {data['email']}")
        return usuario

    usuario = Usuario(password_hash=hash_password(PASSWORD), **data)
    db.add(usuario)
    db.flush()
    creados.append(f"Usuario {data['email']}")
    return usuario


def get_or_create_empresa(db, data, creados, omitidos):
    empresa = db.query(Empresa).filter(Empresa.nombre == data["nombre"]).first()
    if empresa is not None:
        omitidos.append(f"Empresa {data['nombre']}")
        return empresa

    empresa = Empresa(**data)
    db.add(empresa)
    db.flush()
    creados.append(f"Empresa {data['nombre']}")
    return empresa


def ensure_rol(db, empresa, usuario, rol, creados, omitidos):
    relacion = db.get(EmpresaUsuario, (empresa.id, usuario.id))
    if relacion is not None:
        omitidos.append(f"Rol {empresa.nombre}: {usuario.nombre}")
        return

    db.add(EmpresaUsuario(empresa_id=empresa.id, usuario_id=usuario.id, rol=rol))
    creados.append(f"Rol {rol.value} en {empresa.nombre}: {usuario.nombre}")


def get_or_create_oferta(db, empresa, titulo, descripcion, publicada, dias, creados, omitidos):
    oferta = (
        db.query(Oferta)
        .filter(Oferta.empresa_id == empresa.id, Oferta.titulo == titulo)
        .first()
    )
    if oferta is not None:
        omitidos.append(f"Oferta {empresa.nombre}: {titulo}")
        return oferta

    oferta = Oferta(
        empresa_id=empresa.id,
        titulo=titulo,
        descripcion=descripcion,
        publicada=publicada,
        fecha_publicacion=(datetime.now() - timedelta(days=dias)) if publicada else None,
    )
    db.add(oferta)
    db.flush()
    creados.append(f"Oferta {empresa.nombre}: {titulo}")
    return oferta


def ensure_postulacion(db, oferta, usuario, estado, creados, omitidos):
    existente = (
        db.query(Postulacion)
        .filter(
            Postulacion.oferta_id == oferta.id,
            Postulacion.usuario_id == usuario.id,
        )
        .first()
    )
    if existente is not None:
        omitidos.append(f"Postulación {oferta.titulo}: {usuario.nombre}")
        return

    db.add(Postulacion(oferta_id=oferta.id, usuario_id=usuario.id, estado=estado))
    creados.append(f"Postulación {oferta.titulo}: {usuario.nombre} ({estado})")


def ensure_experiencia(db, usuario, empresa, puesto, desde, hasta, creados, omitidos):
    existente = (
        db.query(Experiencia)
        .filter(
            Experiencia.usuario_id == usuario.id,
            Experiencia.empresa_id == empresa.id,
            Experiencia.puesto == puesto,
            Experiencia.desde == desde,
        )
        .first()
    )
    if existente is not None:
        omitidos.append(f"Experiencia {usuario.nombre}: {puesto}")
        return

    db.add(
        Experiencia(
            usuario_id=usuario.id,
            empresa_id=empresa.id,
            puesto=puesto,
            desde=desde,
            hasta=hasta,
        )
    )
    creados.append(f"Experiencia {usuario.nombre}: {puesto}")


def ensure_conexion(db, usuario_a, usuario_b, estado, creados, omitidos):
    existente = (
        db.query(Conexion)
        .filter(
            or_(
                and_(Conexion.usuario_a == usuario_a.id, Conexion.usuario_b == usuario_b.id),
                and_(Conexion.usuario_a == usuario_b.id, Conexion.usuario_b == usuario_a.id),
            )
        )
        .first()
    )
    if existente is not None:
        omitidos.append(f"Conexión {usuario_a.nombre} - {usuario_b.nombre}")
        return

    db.add(Conexion(usuario_a=usuario_a.id, usuario_b=usuario_b.id, estado=estado))
    creados.append(f"Conexión {estado}: {usuario_a.nombre} - {usuario_b.nombre}")


def main():
    creados = []
    omitidos = []

    with SessionLocal() as db:
        try:
            usuarios = {
                data["email"]: get_or_create_usuario(db, data, creados, omitidos)
                for data in USUARIOS
            }
            empresas = {
                data["nombre"]: get_or_create_empresa(db, data, creados, omitidos)
                for data in EMPRESAS
            }

            juan = usuarios["juan.perez@test.com"]
            franco = usuarios["franco.gomez@test.com"]
            pedro = usuarios["pedro.rodriguez@test.com"]
            lucas = usuarios["lucas.fernandez@test.com"]
            martin = usuarios["martin.lopez@test.com"]
            tech = empresas["Tech Solutions"]
            globant = empresas["Globant Test"]
            mercado = empresas["Mercado Digital"]

            for empresa, usuario, rol in [
                (tech, juan, RolEmpresa.OWNER),
                (tech, franco, RolEmpresa.OWNER),
                (tech, pedro, RolEmpresa.RECRUITER),
                (globant, franco, RolEmpresa.OWNER),
                (globant, lucas, RolEmpresa.RECRUITER),
                (mercado, pedro, RolEmpresa.OWNER),
                (mercado, martin, RolEmpresa.RECRUITER),
            ]:
                ensure_rol(db, empresa, usuario, rol, creados, omitidos)

            backend = get_or_create_oferta(
                db, tech, "Desarrollador Backend Python", "API en FastAPI y PostgreSQL.", True, 18, creados, omitidos
            )
            get_or_create_oferta(
                db, tech, "QA Automation", "Automatización de pruebas para producto web.", False, 0, creados, omitidos
            )
            frontend = get_or_create_oferta(
                db, globant, "Desarrollador Frontend React", "Desarrollo de interfaces React.", True, 11, creados, omitidos
            )
            data = get_or_create_oferta(
                db, mercado, "Analista de Datos", "Análisis de métricas de negocio.", True, 7, creados, omitidos
            )
            get_or_create_oferta(
                db, mercado, "Project Manager Digital", "Coordinación de proyectos digitales.", False, 0, creados, omitidos
            )

            for oferta, usuario, estado in [
                (backend, lucas, "nueva"),
                (backend, martin, "vista"),
                (backend, pedro, "entrevista"),
                (frontend, juan, "contratado"),
                (frontend, martin, "rechazada"),
                (data, juan, "vista"),
                (data, franco, "nueva"),
                (data, lucas, "entrevista"),
            ]:
                ensure_postulacion(db, oferta, usuario, estado, creados, omitidos)

            for experiencia in [
                (juan, tech, "Desarrollador Backend", date(2022, 1, 1), None),
                (franco, tech, "Project Manager", date(2020, 1, 1), date(2022, 12, 31)),
                (franco, globant, "Ingeniero de Software", date(2023, 1, 1), None),
                (pedro, tech, "QA Tester", date(2020, 2, 1), date(2022, 12, 31)),
                (pedro, mercado, "Analista de Datos", date(2023, 1, 1), None),
                (lucas, globant, "Desarrollador Frontend", date(2022, 5, 1), None),
                (martin, mercado, "Project Manager", date(2024, 1, 1), None),
            ]:
                ensure_experiencia(db, *experiencia, creados, omitidos)

            for usuario_a, usuario_b, estado in [
                (juan, franco, "aceptada"),
                (juan, pedro, "aceptada"),
                (franco, lucas, "aceptada"),
                (pedro, martin, "aceptada"),
                (franco, pedro, "pendiente"),
                (lucas, martin, "pendiente"),
            ]:
                ensure_conexion(db, usuario_a, usuario_b, estado, creados, omitidos)

            db.commit()
        except Exception:
            db.rollback()
            raise

    print("Seed completado.")
    print(f"Creados: {len(creados)}")
    for item in creados:
        print(f"  + {item}")
    print(f"Omitidos por existir: {len(omitidos)}")
    for item in omitidos:
        print(f"  = {item}")


if __name__ == "__main__":
    main()

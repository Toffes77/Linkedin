import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Date, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.comentario_model import Comentario
from src.db.models.conexiones_model import Conexion
from src.db.models.conversacion_model import Conversacion, ConversacionUsuario, Mensaje
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.experiencia_model import Experiencia
from src.db.models.notificacion_model import Notificacion
from src.db.models.oferta_model import Oferta
from src.db.models.postulacion_model import Postulacion
from src.db.models.promocion_model import Promocion
from src.db.models.publicacion_model import Publicacion
from src.db.models.seguimiento_model import Seguimiento
from src.db.models.solicitud_contratacion_promocion_model import (
    SolicitudContratacionPromocion,
)
from src.db.models.usuario_model import Usuario
from src.dtos.empresa_dto import CreateEmpresaDTO, UpdateEmpresaDTO
from src.dtos.experiencia_dto import CreateExperienciaDTO, UpdateExperienciaDTO
from src.dtos.mensaje_dto import CrearConversacionDTO, EnviarMensajeDTO
from src.dtos.oferta_dto import CreateOfertaDTO, UpdateOfertaDTO
from src.dtos.postulacion_dto import CreatePostulacionDTO
from src.dtos.publicacion_dto import CreatePublicacionDTO, PublicacionResponseDTO, UpdatePublicacionDTO
from src.dtos.usuario_dto import CreateUsuarioDTO, UpdateUsuarioDTO
from src.middlewares.auth_middleware import get_current_user
from src.repositories.solicitud_contratacion_promocion_repository import (
    SolicitudContratacionPromocionRepository,
)
from src.schemas.empresa_schema import CreateEmpresaSchema, UpdateEmpresaSchema
from src.schemas.experiencia_schema import (
    CreateExperienciaSchema,
    UpdateExperienciaSchema,
)
from src.schemas.oferta_schema import CreateOfertaSchema, UpdateOfertaSchema
from src.schemas.publicación_schemas import (
    CreatePublicacionSchema,
    UpdatePublicacionSchema,
)
from src.schemas.usuario_schema import CreateUsuarioSchema, UpdateUsuarioSchema
from src.services.mensaje_service import MensajeService
from src.services.oferta_service import OfertaService
from src.services.postulacion_service import PostulacionService
from src.services.publicacion_service import PublicacionService
from src.utils.datetime_utils import utc_now


WHITESPACE_VALUES = (" ", "     ", "\t", "\n", " \t \n ")


class WhitespaceValidationTests(unittest.TestCase):
    def assert_rejects_whitespace(self, factory) -> None:
        for value in WHITESPACE_VALUES:
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValidationError):
                    factory(value)

    def test_create_and_update_schemas_reject_whitespace_only(self):
        cases = {
            "usuario create nombre": lambda value: CreateUsuarioSchema(
                email="user@example.com",
                password="password-123",
                nombre=value,
                headline="Backend",
                ciudad="Córdoba",
            ),
            "usuario create headline": lambda value: CreateUsuarioSchema(
                email="user@example.com",
                password="password-123",
                nombre="Usuario",
                headline=value,
                ciudad="Córdoba",
            ),
            "usuario create ciudad": lambda value: CreateUsuarioSchema(
                email="user@example.com",
                password="password-123",
                nombre="Usuario",
                headline="Backend",
                ciudad=value,
            ),
            "usuario update": lambda value: UpdateUsuarioSchema(nombre=value),
            "empresa create": lambda value: CreateEmpresaSchema(nombre=value),
            "empresa update": lambda value: UpdateEmpresaSchema(nombre=value),
            "experiencia create": lambda value: CreateExperienciaSchema(
                empresa_id=1,
                puesto=value,
                desde=date(2026, 1, 1),
            ),
            "experiencia update": lambda value: UpdateExperienciaSchema(
                puesto=value
            ),
            "publicacion create": lambda value: CreatePublicacionSchema(
                texto=value
            ),
            "publicacion update": lambda value: UpdatePublicacionSchema(
                texto=value
            ),
            "oferta create titulo": lambda value: CreateOfertaSchema(
                empresa_id=1,
                titulo=value,
                descripcion="Descripción",
            ),
            "oferta create descripcion": lambda value: CreateOfertaSchema(
                empresa_id=1,
                titulo="Backend",
                descripcion=value,
            ),
            "oferta update titulo": lambda value: UpdateOfertaSchema(
                titulo=value
            ),
            "oferta update descripcion": lambda value: UpdateOfertaSchema(
                descripcion=value
            ),
        }
        for name, factory in cases.items():
            with self.subTest(case=name):
                self.assert_rejects_whitespace(factory)

    def test_dtos_apply_the_same_create_and_update_rules(self):
        cases = {
            "usuario create": lambda value: CreateUsuarioDTO(
                email="user@example.com",
                password="password-123",
                nombre=value,
                headline="Backend",
                ciudad="Rosario",
            ),
            "usuario update": lambda value: UpdateUsuarioDTO(headline=value),
            "empresa create": lambda value: CreateEmpresaDTO(nombre=value),
            "empresa update": lambda value: UpdateEmpresaDTO(nombre=value),
            "experiencia create": lambda value: CreateExperienciaDTO(
                usuario_id=1,
                empresa_id=1,
                puesto=value,
                desde=date(2026, 1, 1),
            ),
            "experiencia update": lambda value: UpdateExperienciaDTO(
                puesto=value
            ),
            "publicacion create": lambda value: CreatePublicacionDTO(
                autor_id=1,
                texto=value,
            ),
            "publicacion update": lambda value: UpdatePublicacionDTO(texto=value),
            "oferta create titulo": lambda value: CreateOfertaDTO(
                empresa_id=1,
                titulo=value,
                descripcion="Descripción",
            ),
            "oferta create descripcion": lambda value: CreateOfertaDTO(
                empresa_id=1,
                titulo="Backend",
                descripcion=value,
            ),
            "oferta update": lambda value: UpdateOfertaDTO(descripcion=value),
        }
        for name, factory in cases.items():
            with self.subTest(case=name):
                self.assert_rejects_whitespace(factory)

    def test_domain_text_is_trimmed_without_modifying_passwords(self):
        user = CreateUsuarioSchema(
            email="user@example.com",
            password="  password-123  ",
            nombre="  Juan  ",
            headline="  Backend Developer  ",
            ciudad="  Mendoza  ",
        )
        company = CreateEmpresaSchema(
            nombre="  Atanes  ",
            industria="  Tecnología  ",
        )
        experience = CreateExperienciaSchema(
            empresa_id=1,
            puesto="  Backend Developer  ",
            desde=date(2026, 1, 1),
        )
        publication = CreatePublicacionSchema(texto="  Contenido profesional  ")
        offer = CreateOfertaSchema(
            empresa_id=1,
            titulo="  Python Developer  ",
            descripcion="  Desarrollo de APIs  ",
        )

        self.assertEqual(user.nombre, "Juan")
        self.assertEqual(user.headline, "Backend Developer")
        self.assertEqual(user.ciudad, "Mendoza")
        self.assertEqual(user.password, "  password-123  ")
        self.assertEqual(company.nombre, "Atanes")
        self.assertEqual(company.industria, "Tecnología")
        self.assertEqual(experience.puesto, "Backend Developer")
        self.assertEqual(publication.texto, "Contenido profesional")
        self.assertEqual(offer.titulo, "Python Developer")
        self.assertEqual(offer.descripcion, "Desarrollo de APIs")

    def test_optional_and_absent_update_fields_keep_existing_semantics(self):
        absent = UpdateUsuarioSchema()
        explicit_null = UpdateUsuarioSchema(headline=None)
        optional_company = UpdateEmpresaSchema(industria=None)

        self.assertNotIn("headline", absent.model_fields_set)
        self.assertIn("headline", explicit_null.model_fields_set)
        self.assertIsNone(explicit_null.headline)
        self.assertIsNone(optional_company.industria)


class TextAndDatetimeApiTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_create_endpoints_reject_whitespace_before_service(self):
        requests = (
            (
                "/api/usuarios",
                {
                    "email": "blank@example.com",
                    "password": "password-123",
                    "nombre": " \t\n ",
                    "headline": "Backend",
                    "ciudad": "Rosario",
                },
            ),
            ("/api/empresas", {"nombre": " \t\n "}),
            (
                "/api/usuarios/7/experiencias",
                {
                    "empresa_id": 1,
                    "puesto": " \t\n ",
                    "desde": "2026-01-01",
                },
            ),
            ("/api/publicaciones", {"texto": " \t\n "}),
            (
                "/api/ofertas",
                {
                    "empresa_id": 1,
                    "titulo": "Backend",
                    "descripcion": " \t\n ",
                },
            ),
        )
        for url, payload in requests:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, json=payload).status_code, 422)

    def test_update_endpoints_reject_whitespace_before_service(self):
        requests = (
            ("/api/usuarios/me", {"nombre": " \t\n "}),
            ("/api/empresas/1", {"nombre": " \t\n "}),
            ("/api/publicaciones/1", {"texto": " \t\n "}),
            ("/api/ofertas/1", {"titulo": " \t\n "}),
        )
        for url, payload in requests:
            with self.subTest(url=url):
                self.assertEqual(self.client.put(url, json=payload).status_code, 422)

    def test_api_receives_trimmed_text_and_serializes_utc_offset(self):
        created_at = datetime(2026, 9, 2, 15, 0, tzinfo=timezone.utc)
        returned = PublicacionResponseDTO(
            id=8,
            autor_id=7,
            texto="Contenido",
            fecha=created_at,
        )
        with patch(
            "src.routers.publicacion_router.PublicacionService.create",
            return_value=returned,
        ) as create:
            response = self.client.post(
                "/api/publicaciones",
                json={"texto": "  Contenido  "},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(create.call_args.args[0].texto, "Contenido")
        serialized = response.json()["fecha"]
        parsed = datetime.fromisoformat(serialized.replace("Z", "+00:00"))
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(parsed.utcoffset(), timedelta(0))


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "Estas pruebas requieren la PostgreSQL configurada.",
)
class PostgresDatetimeAndTextIntegrityTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides.clear()
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        suffix = uuid4().hex
        self.owner = Usuario(
            email=f"utc-owner-{suffix}@example.com",
            nombre="Owner UTC",
            password_hash="hash",
            headline="Backend",
            ciudad="Buenos Aires",
        )
        self.candidate = Usuario(
            email=f"utc-candidate-{suffix}@example.com",
            nombre="Candidate UTC",
            password_hash="hash",
            headline="Frontend",
            ciudad="Córdoba",
        )
        self.company = Empresa(nombre=f"UTC Company {suffix}")
        self.db.add_all([self.owner, self.candidate, self.company])
        self.db.flush()
        self.membership = EmpresaUsuario(
            empresa_id=self.company.id,
            usuario_id=self.owner.id,
            rol=RolEmpresa.OWNER,
        )
        self.experience = Experiencia(
            usuario_id=self.owner.id,
            empresa_id=self.company.id,
            puesto="Developer",
            desde=date(2025, 1, 1),
        )
        self.publication = Publicacion(
            autor_id=self.owner.id,
            texto="Publicación válida",
        )
        self.offer = Oferta(
            empresa_id=self.company.id,
            titulo="Oferta válida",
            descripcion="Descripción válida",
        )
        self.promotion = Promocion(
            usuario_id=self.candidate.id,
            titulo="Promoción válida",
            descripcion="Descripción válida",
        )
        self.connection_model = Conexion(
            usuario_a=min(self.owner.id, self.candidate.id),
            usuario_b=max(self.owner.id, self.candidate.id),
            solicitante_id=self.owner.id,
            estado="aceptada",
        )
        self.db.add_all(
            [
                self.membership,
                self.experience,
                self.publication,
                self.offer,
                self.promotion,
                self.connection_model,
            ]
        )
        self.db.flush()
        self.comment = Comentario(
            publicacion_id=self.publication.id,
            usuario_id=self.owner.id,
            contenido="Comentario válido",
        )
        self.conversation = Conversacion(
            usuario_menor_id=min(self.owner.id, self.candidate.id),
            usuario_mayor_id=max(self.owner.id, self.candidate.id),
        )
        self.db.add_all([self.comment, self.conversation])
        self.db.flush()
        self.db.add_all(
            [
                ConversacionUsuario(
                    conversacion_id=self.conversation.id,
                    usuario_id=self.owner.id,
                ),
                ConversacionUsuario(
                    conversacion_id=self.conversation.id,
                    usuario_id=self.candidate.id,
                ),
            ]
        )
        self.db.flush()
        self.message = Mensaje(
            conversacion_id=self.conversation.id,
            autor_id=self.owner.id,
            contenido="Mensaje válido",
            tipo="TEXTO",
        )
        self.db.add(self.message)
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    @staticmethod
    def assert_utc(test_case: unittest.TestCase, value: datetime) -> None:
        test_case.assertIsNotNone(value.tzinfo)
        test_case.assertEqual(value.utcoffset(), timedelta(0))

    def test_models_postgresql_and_session_use_timezone_aware_instants(self):
        expected = {
            "usuario": (Usuario, ("fecha_registro",)),
            "promocion": (Promocion, ("fecha_creacion",)),
            "solicitud_contratacion_promocion": (
                SolicitudContratacionPromocion,
                ("fecha_creacion", "fecha_respuesta"),
            ),
            "publicacion": (Publicacion, ("fecha",)),
            "comentario": (Comentario, ("fecha",)),
            "oferta": (Oferta, ("fecha_publicacion",)),
            "postulacion": (Postulacion, ("fecha",)),
            "conexiones": (Conexion, ("fecha",)),
            "notificacion": (Notificacion, ("fecha",)),
            "seguimiento": (Seguimiento, ("fecha",)),
            "conversacion": (
                Conversacion,
                ("fecha_creacion", "fecha_ultimo_mensaje"),
            ),
            "conversacion_usuario": (ConversacionUsuario, ("ultima_lectura",)),
            "mensaje": (Mensaje, ("fecha",)),
        }
        database = inspect(engine)
        for table_name, (model, column_names) in expected.items():
            database_columns = {
                column["name"]: column for column in database.get_columns(table_name)
            }
            for column_name in column_names:
                with self.subTest(table=table_name, column=column_name):
                    self.assertTrue(
                        getattr(model.__table__.c[column_name].type, "timezone", False)
                    )
                    self.assertTrue(
                        getattr(database_columns[column_name]["type"], "timezone", False)
                    )

        self.assertIs(type(Experiencia.__table__.c.desde.type), Date)
        self.assertIs(type(Experiencia.__table__.c.hasta.type), Date)
        self.assertEqual(self.db.execute(text("SHOW TIMEZONE")).scalar_one(), "UTC")

    def test_new_domain_timestamps_are_aware_and_api_contains_offset(self):
        publication = PublicacionService(self.db).create(
            CreatePublicacionDTO(
                autor_id=self.owner.id,
                texto="Publicación UTC",
            )
        )
        offer = OfertaService(self.db).create(
            CreateOfertaDTO(
                empresa_id=self.company.id,
                titulo="Oferta UTC",
                descripcion="Descripción UTC",
                publicada=True,
            ),
            self.owner.id,
        )
        application = PostulacionService(self.db).create(
            CreatePostulacionDTO(
                oferta_id=offer.id,
                usuario_id=self.candidate.id,
            )
        )
        conversation = MensajeService(self.db).get_or_create(
            CrearConversacionDTO(usuario_id=self.candidate.id),
            self.owner.id,
        )
        message = MensajeService(self.db).send_message(
            conversation.id,
            EnviarMensajeDTO(contenido="Mensaje UTC"),
            self.owner.id,
        )
        follow = Seguimiento(
            seguidor_id=self.candidate.id,
            seguido_id=self.owner.id,
        )
        request = SolicitudContratacionPromocion(
            promocion_id=self.promotion.id,
            empresa_id=self.company.id,
            solicitante_id=self.owner.id,
        )
        self.db.add_all([follow, request])
        self.db.commit()
        SolicitudContratacionPromocionRepository(self.db).accept(request)
        notification = (
            self.db.query(Notificacion)
            .filter(Notificacion.postulacion_id == application.id)
            .one()
        )

        values = (
            self.owner.fecha_registro,
            self.connection_model.fecha,
            self.promotion.fecha_creacion,
            self.comment.fecha,
            publication.fecha,
            offer.fecha_publicacion,
            application.fecha,
            notification.fecha,
            conversation.fecha_creacion,
            message.fecha,
            follow.fecha,
            request.fecha_creacion,
            request.fecha_respuesta,
        )
        for value in values:
            with self.subTest(value=value):
                self.assert_utc(self, value)

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.owner
        response = TestClient(app).get(f"/api/publicaciones/{publication.id}")
        self.assertEqual(response.status_code, 200)
        serialized = response.json()["fecha"]
        parsed = datetime.fromisoformat(serialized.replace("Z", "+00:00"))
        self.assertEqual(parsed.utcoffset(), timedelta(0))

    def test_equivalent_offsets_are_the_same_persisted_instant(self):
        utc_value = datetime(2026, 9, 2, 15, 0, tzinfo=timezone.utc)
        argentina_value = datetime(
            2026,
            9,
            2,
            12,
            0,
            tzinfo=timezone(timedelta(hours=-3)),
        )
        first = Publicacion(
            autor_id=self.owner.id,
            texto="Instante UTC",
            fecha=utc_value,
        )
        second = Publicacion(
            autor_id=self.owner.id,
            texto="Instante con offset",
            fecha=argentina_value,
        )
        self.db.add_all([first, second])
        self.db.commit()
        self.db.refresh(first)
        self.db.refresh(second)

        self.assertEqual(first.fecha, second.fecha)
        self.assertEqual(first.fecha.utcoffset(), timedelta(0))
        self.assertEqual(second.fecha.utcoffset(), timedelta(0))

    def _assert_update_rejected(self, model_type, model_id, field: str) -> None:
        for value in WHITESPACE_VALUES:
            with self.subTest(model=model_type.__name__, field=field, value=repr(value)):
                model = self.db.get(model_type, model_id)
                setattr(model, field, value)
                with self.assertRaises(IntegrityError):
                    self.db.commit()
                self.db.rollback()

    def test_postgresql_checks_reject_spaces_tabs_and_newlines(self):
        self._assert_update_rejected(Usuario, self.owner.id, "nombre")
        self._assert_update_rejected(Usuario, self.owner.id, "headline")
        self._assert_update_rejected(Usuario, self.owner.id, "ciudad")
        self._assert_update_rejected(Empresa, self.company.id, "nombre")
        self._assert_update_rejected(Experiencia, self.experience.id, "puesto")
        self._assert_update_rejected(Oferta, self.offer.id, "titulo")
        self._assert_update_rejected(Oferta, self.offer.id, "descripcion")
        self._assert_update_rejected(Promocion, self.promotion.id, "titulo")
        self._assert_update_rejected(Promocion, self.promotion.id, "descripcion")
        self._assert_update_rejected(Comentario, self.comment.id, "contenido")
        self._assert_update_rejected(Mensaje, self.message.id, "contenido")

        for value in WHITESPACE_VALUES:
            with self.subTest(publication=repr(value)):
                self.db.add(Publicacion(autor_id=self.owner.id, texto=value))
                with self.assertRaises(IntegrityError):
                    self.db.commit()
                self.db.rollback()

    def test_frontend_only_applies_local_timezone_when_presenting(self):
        source = (
            Path(__file__).resolve().parents[2] / "frontend" / "lib" / "format.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("new Date(value)", source)
        self.assertNotIn('`${value}Z`', source)
        self.assertNotIn('value + "Z"', source)
        self.assertIn('new Date(`${value}T12:00:00`)', source)
        self.assertIsNotNone(utc_now().tzinfo)

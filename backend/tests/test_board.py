import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.app import app
from src.db.connection import Base, SessionLocal, engine as postgres_engine, get_db
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.notificacion_model import Notificacion
from src.db.models.promocion_model import Promocion
from src.db.models.solicitud_contratacion_promocion_model import (
    EstadoSolicitudContratacionPromocion,
    SolicitudContratacionPromocion,
)
from src.db.models.usuario_model import Usuario
from src.middlewares.auth_middleware import get_current_user
from src.repositories.promocion_repository import PromocionRepository
from src.repositories.solicitud_contratacion_promocion_repository import (
    SolicitudContratacionPromocionRepository,
)
from src.services.promocion_service import PromocionService
from src.dtos.promocion_dto import CreateSolicitudContratacionPromocionDTO
from src.utils.errors import ConflictError
from src.utils.jwt import create_access_token


def integrity_error(constraint_name: str) -> IntegrityError:
    original = RuntimeError("internal database detail")
    original.diag = SimpleNamespace(constraint_name=constraint_name)
    return IntegrityError("INSERT INTO internal_table", {}, original)


class BoardIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(bind=self.engine)
        self.users = {
            name: self._create_user(name)
            for name in ("owner", "recruiter", "collaborator", "candidate", "outsider")
        }
        self.companies = {
            "owner": self._create_company("Atanes"),
            "recruiter": self._create_company("Software Sur"),
            "collaborator": self._create_company("Colaboradores SA"),
        }
        self.db.add_all(
            [
                EmpresaUsuario(
                    empresa_id=self.companies["owner"].id,
                    usuario_id=self.users["owner"].id,
                    rol=RolEmpresa.OWNER,
                ),
                EmpresaUsuario(
                    empresa_id=self.companies["recruiter"].id,
                    usuario_id=self.users["recruiter"].id,
                    rol=RolEmpresa.RECRUITER,
                ),
                EmpresaUsuario(
                    empresa_id=self.companies["collaborator"].id,
                    usuario_id=self.users["collaborator"].id,
                    rol=RolEmpresa.COLLABORATOR,
                ),
            ]
        )
        self.db.commit()
        self.current_user = self.users["candidate"]
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _create_user(self, name: str) -> Usuario:
        user = Usuario(
            email=f"{name}-{id(self)}@example.com",
            nombre=name.title(),
            password_hash="hash",
            headline=f"Perfil {name}",
            ciudad="Buenos Aires",
        )
        self.db.add(user)
        self.db.flush()
        return user

    def _create_company(self, name: str) -> Empresa:
        company = Empresa(nombre=name, industria="Tecnología")
        self.db.add(company)
        self.db.flush()
        return company

    def _promotion(
        self,
        user: Usuario,
        title: str,
        *,
        date: datetime | None = None,
    ) -> Promocion:
        promotion = Promocion(
            usuario_id=user.id,
            titulo=title,
            descripcion=f"Descripción de {title}",
            fecha_creacion=date or datetime.now(),
        )
        self.db.add(promotion)
        self.db.flush()
        return promotion

    def _request(
        self,
        promotion: Promocion,
        company: Empresa | None = None,
        requester: Usuario | None = None,
    ) -> SolicitudContratacionPromocion:
        request = SolicitudContratacionPromocion(
            promocion_id=promotion.id,
            empresa_id=(company or self.companies["owner"]).id,
            solicitante_id=(requester or self.users["owner"]).id,
            estado=EstadoSolicitudContratacionPromocion.PENDIENTE,
        )
        self.db.add(request)
        self.db.commit()
        return request

    def test_create_promotion_uses_authenticated_user_and_trims_text(self):
        response = self.client.post(
            "/api/promociones",
            json={"titulo": "  Desarrollador Backend  ", "descripcion": "  Python y PostgreSQL.  "},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["usuario_id"], self.users["candidate"].id)
        self.assertEqual(response.json()["titulo"], "Desarrollador Backend")
        self.assertEqual(response.json()["descripcion"], "Python y PostgreSQL.")

    def test_create_promotion_does_not_accept_user_id_from_frontend(self):
        response = self.client.post(
            "/api/promociones",
            json={
                "usuario_id": self.users["owner"].id,
                "titulo": "Backend",
                "descripcion": "Servicios",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["usuario_id"], self.users["candidate"].id)

    def test_create_promotion_requires_authentication(self):
        del app.dependency_overrides[get_current_user]
        response = self.client.post(
            "/api/promociones",
            json={"titulo": "Backend", "descripcion": "Servicios"},
        )
        self.assertEqual(response.status_code, 401, response.text)

    def test_board_promotions_remain_authenticated_even_when_visible_to_users(self):
        del app.dependency_overrides[get_current_user]
        response = self.client.get("/api/promociones")
        self.assertEqual(response.status_code, 401, response.text)

    def test_openapi_keeps_board_auth_and_removes_application_user_id(self):
        schema = app.openapi()
        application_body = schema["components"]["schemas"]["CreatePostulacionSchema"]
        board_operation = schema["paths"]["/api/promociones"]["get"]

        self.assertNotIn("usuario_id", application_body["properties"])
        self.assertFalse(application_body["additionalProperties"])
        self.assertIn("usuarios autenticados", board_operation["description"])
        self.assertIn("No es un acceso anónimo desde Internet", board_operation["description"])
        self.assertEqual(
            board_operation["security"],
            [{"HTTPBearer": []}, {"cookieAuth": []}],
        )
        self.assertIn("/api/experiencias/{experiencia_id}", schema["paths"])
        self.assertIn("put", schema["paths"]["/api/experiencias/{experiencia_id}"])
        self.assertIn("delete", schema["paths"]["/api/experiencias/{experiencia_id}"])

    def test_blank_title_and_description_are_rejected(self):
        for blank in ("", " ", "\t", "\n"):
            for field in ("titulo", "descripcion"):
                payload = {"titulo": "Válido", "descripcion": "Válida"}
                payload[field] = blank
                with self.subTest(field=field, blank=repr(blank)):
                    before = self.db.query(Promocion).count()
                    response = self.client.post("/api/promociones", json=payload)
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertEqual(self.db.query(Promocion).count(), before)

    def test_promotion_text_limits_are_enforced(self):
        for payload in (
            {"titulo": "x" * 161, "descripcion": "Válida"},
            {"titulo": "Válido", "descripcion": "x" * 3001},
        ):
            with self.subTest(payload_lengths={key: len(value) for key, value in payload.items()}):
                response = self.client.post("/api/promociones", json=payload)
                self.assertEqual(response.status_code, 422, response.text)

        accepted = self.client.post(
            "/api/promociones",
            json={"titulo": "x" * 160, "descripcion": "x" * 3000},
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)

    def test_public_board_excludes_current_users_promotions(self):
        self._promotion(self.users["candidate"], "Propia")
        other = self._promotion(self.users["outsider"], "Ajena")
        self.db.commit()
        response = self.client.get("/api/promociones")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()["items"]], [other.id])

    def test_my_promotions_returns_complete_history_newest_first(self):
        first = self._promotion(self.users["candidate"], "Primera", date=datetime.now() - timedelta(days=1))
        second = self._promotion(self.users["candidate"], "Segunda")
        self.db.commit()
        response = self.client.get("/api/promociones/mias")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()["items"]], [second.id, first.id])

    def test_public_board_returns_only_latest_promotion_per_user(self):
        first = self._promotion(self.users["outsider"], "Programador Java", date=datetime.now() - timedelta(days=1))
        latest = self._promotion(self.users["outsider"], "Desarrollador Python")
        self.db.commit()
        response = self.client.get("/api/promociones")
        ids = [item["id"] for item in response.json()["items"]]
        self.assertEqual(ids, [latest.id])
        self.assertNotIn(first.id, ids)

    def test_public_order_is_date_descending_with_stable_id_tiebreaker(self):
        tied = datetime(2026, 8, 26, 12, 0, 0)
        first = self._promotion(self.users["owner"], "Owner", date=tied)
        second = self._promotion(self.users["outsider"], "Outsider", date=tied)
        self.db.commit()
        response = self.client.get("/api/promociones")
        self.assertEqual([item["id"] for item in response.json()["items"]], [second.id, first.id])

    def test_search_is_partial_case_insensitive_and_trimmed(self):
        match = self._promotion(self.users["outsider"], "Desarrollador Backend")
        self._promotion(self.users["owner"], "Técnico electrónico")
        self.db.commit()
        for query in ("desarro", "DESARROLLADOR", "  Backend  "):
            with self.subTest(query=query):
                response = self.client.get("/api/promociones", params={"q": query})
                self.assertEqual([item["id"] for item in response.json()["items"]], [match.id])

    def test_search_never_revives_an_older_matching_promotion(self):
        self._promotion(self.users["outsider"], "Desarrollador Java", date=datetime.now() - timedelta(days=1))
        self._promotion(self.users["outsider"], "Técnico electrónico")
        self.db.commit()
        response = self.client.get("/api/promociones", params={"q": "Desarrollador"})
        self.assertEqual(response.json()["items"], [])

    def test_public_pagination_runs_after_latest_per_user_selection(self):
        extra_users = [self._create_user(f"extra-{index}") for index in range(3)]
        for index, user in enumerate(extra_users):
            self._promotion(user, f"Profesión {index}", date=datetime.now() + timedelta(minutes=index))
        self.db.commit()
        first = self.client.get("/api/promociones", params={"page": 1, "page_size": 2}).json()
        second = self.client.get("/api/promociones", params={"page": 2, "page_size": 2}).json()
        self.assertEqual(first["total"], 3)
        self.assertEqual(len(first["items"]), 2)
        self.assertEqual(len(second["items"]), 1)
        self.assertTrue(set(item["id"] for item in first["items"]).isdisjoint(item["id"] for item in second["items"]))

    def test_my_promotions_cursor_pages_are_scoped_stable_and_disjoint(self):
        base = datetime(2026, 8, 26, 12, 0, 0)
        own = [
            self._promotion(
                self.users["candidate"],
                f"Propia {index}",
                date=base + timedelta(minutes=index),
            )
            for index in range(3)
        ]
        self._promotion(self.users["outsider"], "Ajena", date=base + timedelta(hours=1))
        self.db.commit()

        first = self.client.get("/api/promociones/mias", params={"limit": 2})
        self.assertEqual(first.status_code, 200, first.text)
        first_body = first.json()
        self.assertTrue(first_body["has_more"])
        self.assertIsNotNone(first_body["next_cursor"])
        second = self.client.get(
            "/api/promociones/mias",
            params={"limit": 2, "cursor": first_body["next_cursor"]},
        )
        self.assertEqual(second.status_code, 200, second.text)
        rows = first_body["items"] + second.json()["items"]
        ids = [item["id"] for item in rows]
        self.assertEqual(ids, [own[2].id, own[1].id, own[0].id])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(
            item["usuario_id"] == self.users["candidate"].id
            for item in rows
        ))

    def test_invalid_pagination_inputs_are_controlled(self):
        for path, params, expected in (
            ("/api/promociones", {"page": 0}, 422),
            ("/api/promociones", {"page_size": 0}, 422),
            ("/api/promociones", {"page_size": 51}, 422),
            ("/api/promociones/mias", {"limit": 0}, 422),
            ("/api/promociones/mias", {"limit": 51}, 422),
            ("/api/promociones/mias", {"cursor": "cursor-inválido"}, 400),
        ):
            with self.subTest(path=path, params=params):
                response = self.client.get(path, params=params)
                self.assertEqual(response.status_code, expected, response.text)

    def test_hiring_company_selector_only_returns_manager_roles(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        self.db.commit()
        self.current_user = self.users["owner"]
        response = self.client.get(f"/api/promociones/{promotion.id}/empresas-contratantes")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()[0]["empresa_id"], self.companies["owner"].id)
        self.current_user = self.users["collaborator"]
        denied = self.client.get(f"/api/promociones/{promotion.id}/empresas-contratantes")
        self.assertEqual(denied.json(), [])

    def test_selector_excludes_company_where_candidate_is_already_member(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        self.db.add(EmpresaUsuario(
            empresa_id=self.companies["owner"].id,
            usuario_id=self.users["candidate"].id,
            rol=RolEmpresa.COLLABORATOR,
        ))
        self.db.commit()
        self.current_user = self.users["owner"]
        response = self.client.get(f"/api/promociones/{promotion.id}/empresas-contratantes")
        self.assertEqual(response.json(), [])

    def test_owner_can_create_pending_request_and_persistent_notification(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        self.db.commit()
        self.current_user = self.users["owner"]
        response = self.client.post(
            f"/api/promociones/{promotion.id}/solicitudes-contratacion",
            json={"empresa_id": self.companies["owner"].id},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["estado"], "PENDIENTE")
        notification = self.db.query(Notificacion).one()
        self.assertEqual(notification.usuario_id, self.users["candidate"].id)
        self.assertEqual(notification.tipo, "CONTRATACION_PROMOCION")
        self.assertEqual(notification.promocion_id, promotion.id)
        self.assertIn("Atanes", notification.mensaje)

    def test_recruiter_can_create_request(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        self.db.commit()
        self.current_user = self.users["recruiter"]
        response = self.client.post(
            f"/api/promociones/{promotion.id}/solicitudes-contratacion",
            json={"empresa_id": self.companies["recruiter"].id},
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_collaborator_and_outsider_cannot_create_request(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        self.db.commit()
        for user, company in (
            (self.users["collaborator"], self.companies["collaborator"]),
            (self.users["outsider"], self.companies["owner"]),
        ):
            with self.subTest(user=user.nombre):
                self.current_user = user
                response = self.client.post(
                    f"/api/promociones/{promotion.id}/solicitudes-contratacion",
                    json={"empresa_id": company.id},
                )
                self.assertEqual(response.status_code, 403, response.text)

    def test_user_cannot_hire_own_promotion(self):
        promotion = self._promotion(self.users["owner"], "Backend")
        self.db.commit()
        self.current_user = self.users["owner"]
        response = self.client.post(
            f"/api/promociones/{promotion.id}/solicitudes-contratacion",
            json={"empresa_id": self.companies["owner"].id},
        )
        self.assertEqual(response.status_code, 409, response.text)

    def test_company_cannot_hire_existing_member(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        self.db.add(EmpresaUsuario(
            empresa_id=self.companies["owner"].id,
            usuario_id=self.users["candidate"].id,
            rol=RolEmpresa.COLLABORATOR,
        ))
        self.db.commit()
        self.current_user = self.users["owner"]
        response = self.client.post(
            f"/api/promociones/{promotion.id}/solicitudes-contratacion",
            json={"empresa_id": self.companies["owner"].id},
        )
        self.assertEqual(response.status_code, 409, response.text)

    def test_duplicate_pending_request_is_rejected(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        self._request(promotion)
        self.current_user = self.users["owner"]
        response = self.client.post(
            f"/api/promociones/{promotion.id}/solicitudes-contratacion",
            json={"empresa_id": self.companies["owner"].id},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.db.query(SolicitudContratacionPromocion).count(), 1)
        self.assertEqual(self.db.query(Notificacion).count(), 0)
        self.assertNotIn("uq_solicitud", response.text)
        self.assertNotIn("INSERT INTO", response.text)
        self.assertEqual(self.db.execute(text("SELECT 1")).scalar_one(), 1)

    def test_missing_company_and_promotion_are_controlled(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        self.db.commit()
        self.current_user = self.users["owner"]
        missing_company = self.client.post(
            f"/api/promociones/{promotion.id}/solicitudes-contratacion",
            json={"empresa_id": 1_000_000},
        )
        missing_promotion = self.client.post(
            "/api/promociones/1000000/solicitudes-contratacion",
            json={"empresa_id": self.companies["owner"].id},
        )
        self.assertEqual(missing_company.status_code, 404, missing_company.text)
        self.assertEqual(missing_promotion.status_code, 404, missing_promotion.text)
        self.assertEqual(self.db.query(SolicitudContratacionPromocion).count(), 0)

    def test_my_promotion_exposes_pending_company_and_status(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        request = self._request(promotion)
        response = self.client.get("/api/promociones/mias")
        item = response.json()["items"][0]
        self.assertEqual(item["estado"], "PENDIENTE_CONTRATACION")
        self.assertEqual(item["solicitudes_pendientes"][0]["id"], request.id)
        self.assertEqual(item["solicitudes_pendientes"][0]["empresa_nombre"], "Atanes")

    def test_candidate_can_accept_and_becomes_collaborator(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        request = self._request(promotion)
        response = self.client.post(f"/api/solicitudes-contratacion-promocion/{request.id}/aceptar")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["estado"], "ACEPTADA")
        self.assertIsNotNone(response.json()["fecha_respuesta"])
        membership = self.db.get(
            EmpresaUsuario,
            (self.companies["owner"].id, self.users["candidate"].id),
        )
        self.assertEqual(membership.rol, RolEmpresa.COLLABORATOR)

    def test_acceptance_hides_promotion_but_preserves_internal_record(self):
        promotion = self._promotion(self.users["candidate"], "Backend ocultable")
        request = self._request(promotion)

        accepted = self.client.post(
            f"/api/solicitudes-contratacion-promocion/{request.id}/aceptar"
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)

        self.current_user = self.users["outsider"]
        public = self.client.get("/api/promociones")
        searched = self.client.get("/api/promociones", params={"q": "ocultable"})
        self.assertNotIn(promotion.id, [item["id"] for item in public.json()["items"]])
        self.assertEqual(searched.json()["items"], [])

        self.current_user = self.users["candidate"]
        mine = self.client.get("/api/promociones/mias")
        self.assertIn(promotion.id, [item["id"] for item in mine.json()["items"]])
        self.assertIsNotNone(self.db.get(Promocion, promotion.id))

    def test_accepted_promotion_cannot_receive_more_requests(self):
        promotion = self._promotion(self.users["candidate"], "Backend contratado")
        request = self._request(promotion)
        accepted = self.client.post(
            f"/api/solicitudes-contratacion-promocion/{request.id}/aceptar"
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)

        self.current_user = self.users["owner"]
        before = self.db.query(SolicitudContratacionPromocion).count()
        blocked = self.client.post(
            f"/api/promociones/{promotion.id}/solicitudes-contratacion",
            json={"empresa_id": self.companies["owner"].id},
        )
        selector = self.client.get(
            f"/api/promociones/{promotion.id}/empresas-contratantes"
        )
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertEqual(selector.status_code, 409, selector.text)
        self.assertIn("no está disponible", blocked.json()["message"])
        self.assertEqual(self.db.query(SolicitudContratacionPromocion).count(), before)

    def test_another_user_cannot_accept_request(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        request = self._request(promotion)
        self.current_user = self.users["outsider"]
        response = self.client.post(f"/api/solicitudes-contratacion-promocion/{request.id}/aceptar")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(request.estado, EstadoSolicitudContratacionPromocion.PENDIENTE)

    def test_request_cannot_be_accepted_twice(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        request = self._request(promotion)
        first = self.client.post(f"/api/solicitudes-contratacion-promocion/{request.id}/aceptar")
        second = self.client.post(f"/api/solicitudes-contratacion-promocion/{request.id}/aceptar")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 409, second.text)

    def test_accepting_does_not_duplicate_or_downgrade_existing_membership(self):
        for role in (RolEmpresa.COLLABORATOR, RolEmpresa.OWNER, RolEmpresa.RECRUITER):
            with self.subTest(role=role):
                company = self._create_company(f"Empresa {role.value}")
                promotion = self._promotion(self.users["candidate"], f"Promoción {role.value}")
                request = self._request(promotion, company=company)
                self.db.add(EmpresaUsuario(
                    empresa_id=company.id,
                    usuario_id=self.users["candidate"].id,
                    rol=role,
                ))
                self.db.commit()
                response = self.client.post(f"/api/solicitudes-contratacion-promocion/{request.id}/aceptar")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(self.db.get(EmpresaUsuario, (company.id, self.users["candidate"].id)).rol, role)
                self.assertEqual(
                    self.db.query(EmpresaUsuario).filter_by(
                        empresa_id=company.id,
                        usuario_id=self.users["candidate"].id,
                    ).count(),
                    1,
                )

    def test_notification_failure_rolls_back_hiring_request(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        self.db.commit()
        self.current_user = self.users["owner"]
        with patch(
            "src.services.promocion_service.NotificacionService.create_many",
            side_effect=RuntimeError("notification failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "notification failed"):
                self.client.post(
                    f"/api/promociones/{promotion.id}/solicitudes-contratacion",
                    json={"empresa_id": self.companies["owner"].id},
                )
        self.assertEqual(self.db.query(SolicitudContratacionPromocion).count(), 0)
        self.assertEqual(self.db.query(Notificacion).count(), 0)

    def test_acceptance_failure_rolls_back_membership_and_status(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        request = self._request(promotion)
        with patch(
            "src.repositories.solicitud_contratacion_promocion_repository.SolicitudContratacionPromocionRepository.accept",
            side_effect=RuntimeError("accept failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "accept failed"):
                self.client.post(f"/api/solicitudes-contratacion-promocion/{request.id}/aceptar")
        self.assertIsNone(self.db.get(
            EmpresaUsuario,
            (self.companies["owner"].id, self.users["candidate"].id),
        ))
        self.db.refresh(request)
        self.assertEqual(request.estado, EstadoSolicitudContratacionPromocion.PENDIENTE)
        self.current_user = self.users["outsider"]
        public = self.client.get("/api/promociones", params={"q": "Backend"})
        self.assertIn(promotion.id, [item["id"] for item in public.json()["items"]])

    def test_existing_notification_endpoints_include_board_notification(self):
        promotion = self._promotion(self.users["candidate"], "Backend")
        request = self._request(promotion)
        self.db.add(Notificacion(
            usuario_id=self.users["candidate"].id,
            tipo="CONTRATACION_PROMOCION",
            mensaje="Atanes quiere contratarte.",
            promocion_id=promotion.id,
            solicitud_contratacion_promocion_id=request.id,
        ))
        self.db.commit()
        listed = self.client.get("/api/notificaciones")
        counted = self.client.get("/api/notificaciones/no-leidas/count")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()[0]["tipo"], "CONTRATACION_PROMOCION")
        self.assertEqual(counted.json(), {"cantidad": 1})


class BoardIntegrityMappingTests(unittest.TestCase):
    def test_unknown_hiring_request_integrity_error_is_rolled_back_and_reraised(self):
        db = Mock()
        service = PromocionService(db)
        service.repository = Mock()
        service.repository.get_by_id.return_value = SimpleNamespace(
            id=10,
            usuario_id=20,
        )
        service.hiring_request_repository = Mock()
        service.hiring_request_repository.get_accepted_for_promotion.return_value = None
        service.hiring_request_repository.get_pending.return_value = None
        unknown = integrity_error("unexpected_foreign_key")
        service.hiring_request_repository.create.side_effect = unknown
        service.company_repository = Mock()
        service.company_repository.get_by_id.return_value = SimpleNamespace(
            id=30,
            nombre="Empresa",
        )
        service.membership_repository = Mock()
        service.membership_repository.has_any_role.return_value = True
        service.membership_repository.get_by_empresa_and_usuario.return_value = None

        with self.assertRaises(IntegrityError) as raised:
            service.create_hiring_request(
                10,
                CreateSolicitudContratacionPromocionDTO(empresa_id=30),
                current_user_id=40,
            )

        self.assertIs(raised.exception, unknown)
        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()


@unittest.skipUnless(
    postgres_engine.dialect.name == "postgresql",
    "La prueba del anti-spam del Tablón requiere la PostgreSQL configurada.",
)
class BoardPostgresTests(unittest.TestCase):
    def setUp(self):
        self.connection = postgres_engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        suffix = uuid4().hex
        self.users = [
            Usuario(
                email=f"board-postgres-{index}-{suffix}@example.com",
                nombre=f"Profesional {index}",
                password_hash="not-used",
                headline="Prueba PostgreSQL del Tablón",
                ciudad="Buenos Aires",
            )
            for index in range(3)
        ]
        self.db.add_all(self.users)
        self.db.flush()
        base_date = datetime(2026, 8, 26, 10, 0, 0)
        self.db.add_all([
            Promocion(usuario_id=self.users[0].id, titulo="Desarrollador Java", descripcion="Histórica", fecha_creacion=base_date),
            Promocion(usuario_id=self.users[0].id, titulo="Técnico electrónico", descripcion="Actual", fecha_creacion=base_date + timedelta(hours=1)),
            Promocion(usuario_id=self.users[1].id, titulo="Desarrollador Backend", descripcion="Actual", fecha_creacion=base_date + timedelta(hours=2)),
            Promocion(usuario_id=self.users[2].id, titulo="Desarrollador propio", descripcion="Propia", fecha_creacion=base_date + timedelta(hours=3)),
        ])
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def test_postgresql_ranks_before_search_excludes_own_and_paginates(self):
        items, total = PromocionRepository(self.db).get_board_page(
            self.users[2].id,
            title="desarrollador",
            page=1,
            page_size=1,
        )

        self.assertEqual(total, 1)
        self.assertEqual([item.titulo for item in items], ["Desarrollador Backend"])

    def test_postgresql_hides_accepted_latest_without_reviving_older_promotion(self):
        company = Empresa(nombre=f"Board accepted {uuid4().hex}")
        self.db.add(company)
        self.db.flush()
        latest = (
            self.db.query(Promocion)
            .filter(Promocion.usuario_id == self.users[0].id)
            .order_by(Promocion.fecha_creacion.desc())
            .first()
        )
        self.db.add(
            SolicitudContratacionPromocion(
                promocion_id=latest.id,
                empresa_id=company.id,
                solicitante_id=self.users[1].id,
                estado=EstadoSolicitudContratacionPromocion.ACEPTADA,
            )
        )
        self.db.flush()

        items, total = PromocionRepository(self.db).get_board_page(
            self.users[2].id,
            title=None,
            page=1,
            page_size=20,
        )

        self.assertNotIn(latest.id, [item.id for item in items])
        self.assertFalse(any(item.usuario_id == self.users[0].id for item in items))
        self.assertEqual(total, 1)


@unittest.skipUnless(
    postgres_engine.dialect.name == "postgresql",
    "Las carreras del Tablón requieren la PostgreSQL configurada.",
)
class BoardConcurrencyPostgresTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex
        with SessionLocal() as db:
            owner = Usuario(
                email=f"board-owner-{suffix}@example.com",
                nombre=f"Board Owner {suffix}",
                password_hash="not-used",
                headline="Owner temporal del Tablón",
                ciudad="Argentina, Buenos Aires",
            )
            candidate = Usuario(
                email=f"board-candidate-{suffix}@example.com",
                nombre=f"Board Candidate {suffix}",
                password_hash="not-used",
                headline="Candidate temporal del Tablón",
                ciudad="Argentina, Córdoba",
            )
            outsider = Usuario(
                email=f"board-outsider-{suffix}@example.com",
                nombre=f"Board Outsider {suffix}",
                password_hash="not-used",
                headline="Outsider temporal del Tablón",
                ciudad="Argentina, Rosario",
            )
            company = Empresa(
                nombre=f"Board Company {suffix}",
                industria="Pruebas de integración",
            )
            db.add_all([owner, candidate, outsider, company])
            db.flush()
            db.add(
                EmpresaUsuario(
                    empresa_id=company.id,
                    usuario_id=owner.id,
                    rol=RolEmpresa.OWNER,
                )
            )
            promotion = Promocion(
                usuario_id=candidate.id,
                titulo=f"[ATANES-BOARD-TEST] {suffix}",
                descripcion="Registro temporal para comprobar concurrencia.",
            )
            db.add(promotion)
            db.commit()
            self.owner_id = owner.id
            self.owner_email = owner.email
            self.candidate_id = candidate.id
            self.outsider_id = outsider.id
            self.company_id = company.id
            self.promotion_id = promotion.id
        self.user_ids = [self.owner_id, self.candidate_id, self.outsider_id]

    def tearDown(self):
        with SessionLocal() as db:
            db.query(Notificacion).filter(
                or_(
                    Notificacion.usuario_id.in_(self.user_ids),
                    Notificacion.usuario_origen_id.in_(self.user_ids),
                    Notificacion.promocion_id == self.promotion_id,
                )
            ).delete(synchronize_session=False)
            db.query(SolicitudContratacionPromocion).filter(
                SolicitudContratacionPromocion.promocion_id == self.promotion_id
            ).delete(synchronize_session=False)
            db.query(EmpresaUsuario).filter(
                EmpresaUsuario.empresa_id == self.company_id
            ).delete(synchronize_session=False)
            db.query(Promocion).filter(Promocion.id == self.promotion_id).delete(
                synchronize_session=False
            )
            db.query(Empresa).filter(Empresa.id == self.company_id).delete(
                synchronize_session=False
            )
            db.query(Usuario).filter(Usuario.id.in_(self.user_ids)).delete(
                synchronize_session=False
            )
            db.commit()

    def _pending_request(self) -> int:
        with SessionLocal() as db:
            request = SolicitudContratacionPromocion(
                promocion_id=self.promotion_id,
                empresa_id=self.company_id,
                solicitante_id=self.owner_id,
                estado=EstadoSolicitudContratacionPromocion.PENDIENTE,
            )
            db.add(request)
            db.commit()
            return request.id

    def test_concurrent_duplicate_requests_return_one_created_and_one_safe_conflict(self):
        barrier = Barrier(2)
        token = create_access_token(
            {"sub": str(self.owner_id), "email": self.owner_email}
        )

        def synchronized_missing(_repository, _promotion_id, _company_id):
            barrier.wait(timeout=10)
            return None

        def send_request():
            with TestClient(app) as client:
                return client.post(
                    f"/api/promociones/{self.promotion_id}/solicitudes-contratacion",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"empresa_id": self.company_id},
                )

        with patch.object(
            SolicitudContratacionPromocionRepository,
            "get_pending",
            autospec=True,
            side_effect=synchronized_missing,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(executor.map(lambda _index: send_request(), range(2)))

        self.assertEqual(sorted(response.status_code for response in responses), [201, 409])
        conflict = next(response for response in responses if response.status_code == 409)
        self.assertIn("propuesta pendiente", conflict.json()["message"])
        self.assertNotIn("uq_solicitud", conflict.text)
        self.assertNotIn("INSERT INTO", conflict.text)
        with SessionLocal() as db:
            self.assertEqual(
                db.query(SolicitudContratacionPromocion)
                .filter_by(promocion_id=self.promotion_id, empresa_id=self.company_id)
                .count(),
                1,
            )
            self.assertEqual(
                db.query(Notificacion)
                .filter_by(
                    usuario_id=self.candidate_id,
                    promocion_id=self.promotion_id,
                    tipo="CONTRATACION_PROMOCION",
                )
                .count(),
                1,
            )
            self.assertEqual(db.execute(text("SELECT 1")).scalar_one(), 1)

    def test_concurrent_double_acceptance_has_one_effect(self):
        request_id = self._pending_request()
        barrier = Barrier(2)

        def accept_request(_index):
            with SessionLocal() as db:
                barrier.wait(timeout=10)
                try:
                    PromocionService(db).accept_hiring_request(
                        request_id,
                        self.candidate_id,
                    )
                    return "accepted"
                except ConflictError:
                    return "conflict"

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(accept_request, range(2)))

        self.assertCountEqual(outcomes, ["accepted", "conflict"])
        with SessionLocal() as db:
            request = db.get(SolicitudContratacionPromocion, request_id)
            membership = db.get(
                EmpresaUsuario,
                (self.company_id, self.candidate_id),
            )
            self.assertEqual(request.estado, EstadoSolicitudContratacionPromocion.ACEPTADA)
            self.assertEqual(membership.rol, RolEmpresa.COLLABORATOR)
            self.assertEqual(
                db.query(EmpresaUsuario)
                .filter_by(empresa_id=self.company_id, usuario_id=self.candidate_id)
                .count(),
                1,
            )

    def test_concurrent_membership_insert_is_recovered_and_preserves_role(self):
        request_id = self._pending_request()
        with SessionLocal() as db:
            service = PromocionService(db)
            original_get = service.membership_repository.get_by_empresa_and_usuario
            first_lookup = True

            def get_with_concurrent_insert(empresa_id, usuario_id):
                nonlocal first_lookup
                if first_lookup:
                    first_lookup = False
                    with SessionLocal() as concurrent_db:
                        concurrent_db.add(
                            EmpresaUsuario(
                                empresa_id=empresa_id,
                                usuario_id=usuario_id,
                                rol=RolEmpresa.RECRUITER,
                            )
                        )
                        concurrent_db.commit()
                    return None
                return original_get(empresa_id, usuario_id)

            service.membership_repository.get_by_empresa_and_usuario = (
                get_with_concurrent_insert
            )
            result = service.accept_hiring_request(request_id, self.candidate_id)
            self.assertEqual(result.estado, EstadoSolicitudContratacionPromocion.ACEPTADA)

        with SessionLocal() as db:
            membership = db.get(
                EmpresaUsuario,
                (self.company_id, self.candidate_id),
            )
            self.assertEqual(membership.rol, RolEmpresa.RECRUITER)
            self.assertEqual(
                db.query(EmpresaUsuario)
                .filter_by(empresa_id=self.company_id, usuario_id=self.candidate_id)
                .count(),
                1,
            )
            visible, _total = PromocionRepository(db).get_board_page(
                self.outsider_id,
                title=None,
                page=1,
                page_size=50,
            )
            self.assertNotIn(self.promotion_id, [promotion.id for promotion in visible])


if __name__ == "__main__":
    unittest.main()

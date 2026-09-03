import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.app import app
from src.db.connection import Base, engine as postgres_engine, get_db
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

    def test_blank_title_and_description_are_rejected(self):
        for payload in (
            {"titulo": "   ", "descripcion": "Válida"},
            {"titulo": "Válido", "descripcion": "   "},
        ):
            with self.subTest(payload=payload):
                response = self.client.post("/api/promociones", json=payload)
                self.assertEqual(response.status_code, 422, response.text)

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
        items, total = PromocionRepository(self.db).get_public_page(
            self.users[2].id,
            title="desarrollador",
            page=1,
            page_size=1,
        )

        self.assertEqual(total, 1)
        self.assertEqual([item.titulo for item in items], ["Desarrollador Backend"])


if __name__ == "__main__":
    unittest.main()

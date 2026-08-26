import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src.app import app
from src.db.connection import get_db
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.dtos.empresa_dto import UpdateEmpresaDTO
from src.dtos.empresa_usuario_dto import CreateEmpresaUsuarioDTO
from src.dtos.oferta_dto import CreateOfertaDTO, UpdateOfertaDTO
from src.dtos.postulacion_dto import UpdatePostulacionDTO
from src.middlewares.auth_middleware import get_current_user
from src.services.empresa_service import EmpresaService
from src.services.empresa_usuario_service import EmpresaUsuarioService
from src.services.oferta_service import OfertaService
from src.services.postulacion_service import PostulacionService
from src.utils.errors import ConflictError, ForbiddenError


def company(company_id: int = 3):
    return SimpleNamespace(
        id=company_id,
        nombre="Empresa colaboradora",
        industria="Tecnología",
        sitio_web=None,
        foto_perfil_url=None,
    )


def allows(role: RolEmpresa):
    return lambda _company_id, _user_id, roles: role in roles


class CollaboratorMembershipTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides.clear()

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_owner_can_manually_add_a_collaborator(self):
        service = EmpresaUsuarioService(Mock())
        service.empresa_repository = Mock()
        service.empresa_repository.get_by_id.return_value = company()
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=9)
        service.repository = Mock()
        service.repository.has_any_role.side_effect = allows(RolEmpresa.OWNER)
        service.repository.get_by_empresa_and_usuario.return_value = None
        service.repository.create.side_effect = lambda relation: relation

        result = service.create(
            3,
            CreateEmpresaUsuarioDTO(
                usuario_id=9,
                rol=RolEmpresa.COLLABORATOR,
            ),
            usuario_actual_id=1,
        )

        created = service.repository.create.call_args.args[0]
        self.assertIsInstance(created, EmpresaUsuario)
        self.assertEqual(created.empresa_id, 3)
        self.assertEqual(created.usuario_id, 9)
        self.assertEqual(created.rol, RolEmpresa.COLLABORATOR)
        self.assertEqual(result.rol, RolEmpresa.COLLABORATOR)

    def test_collaborator_appears_in_company_members(self):
        service = EmpresaUsuarioService(Mock())
        service.empresa_repository = Mock()
        service.empresa_repository.get_by_id.return_value = company()
        service.repository = Mock()
        service.repository.has_any_role.side_effect = allows(RolEmpresa.OWNER)
        service.repository.get_by_empresa.return_value = [
            SimpleNamespace(
                empresa_id=3,
                usuario_id=9,
                rol=RolEmpresa.COLLABORATOR,
            )
        ]

        members = service.get_by_empresa(3, usuario_actual_id=1)

        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].rol, RolEmpresa.COLLABORATOR)

    def test_collaborator_company_appears_in_current_user_companies(self):
        service = EmpresaUsuarioService(Mock())
        service.repository = Mock()
        service.repository.get_by_usuario.return_value = [
            SimpleNamespace(empresa=company(), rol=RolEmpresa.COLLABORATOR)
        ]

        memberships = service.get_by_current_user(9)

        self.assertEqual(len(memberships), 1)
        self.assertEqual(memberships[0].rol, RolEmpresa.COLLABORATOR)

    def test_member_endpoint_accepts_and_returns_collaborator(self):
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
        response_dto = SimpleNamespace(
            empresa_id=3,
            usuario_id=9,
            rol=RolEmpresa.COLLABORATOR,
        )

        with patch(
            "src.routers.empresa_router.EmpresaUsuarioService.create",
            return_value=response_dto,
        ) as create_member:
            response = TestClient(app).post(
                "/api/empresas/3/usuarios",
                json={"usuario_id": 9, "rol": "COLLABORATOR"},
            )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["rol"], "COLLABORATOR")
        self.assertEqual(
            create_member.call_args.args[1].rol,
            RolEmpresa.COLLABORATOR,
        )


class CollaboratorPermissionTests(unittest.TestCase):
    def test_collaborator_cannot_edit_company(self):
        service = EmpresaService(Mock())
        service.repository = Mock()
        service.repository.get_by_id.return_value = company()
        service.empresa_usuario_repository = Mock()
        service.empresa_usuario_repository.has_any_role.side_effect = allows(
            RolEmpresa.COLLABORATOR
        )

        with self.assertRaises(ForbiddenError):
            service.update(3, UpdateEmpresaDTO(nombre="Nuevo nombre"), 9)

        service.repository.update.assert_not_called()

    def test_collaborator_cannot_change_company_logo(self):
        service = EmpresaService(Mock())
        service.repository = Mock()
        service.repository.get_by_id.return_value = company()
        service.empresa_usuario_repository = Mock()
        service.empresa_usuario_repository.has_any_role.side_effect = allows(
            RolEmpresa.COLLABORATOR
        )

        with self.assertRaises(ForbiddenError):
            service.update_profile_photo(3, 9, "logo.png", b"not-an-image")

        service.repository.update_profile_photo.assert_not_called()

    def test_collaborator_cannot_administer_members(self):
        service = EmpresaUsuarioService(Mock())
        service.empresa_repository = Mock()
        service.empresa_repository.get_by_id.return_value = company()
        service.repository = Mock()
        service.repository.has_any_role.side_effect = allows(RolEmpresa.COLLABORATOR)

        with self.assertRaises(ForbiddenError):
            service.get_by_empresa(3, usuario_actual_id=9)

        service.repository.get_by_empresa.assert_not_called()

    def offer_service_for_collaborator(self) -> OfertaService:
        service = OfertaService(Mock())
        service.repository = Mock()
        service.empresa_repository = Mock()
        service.empresa_repository.get_by_id.return_value = company()
        service.empresa_usuario_repository = Mock()
        service.empresa_usuario_repository.has_any_role.side_effect = allows(
            RolEmpresa.COLLABORATOR
        )
        service.postulacion_repository = Mock()
        return service

    def test_collaborator_cannot_create_offers(self):
        service = self.offer_service_for_collaborator()

        with self.assertRaises(ForbiddenError):
            service.create(
                CreateOfertaDTO(
                    empresa_id=3,
                    titulo="Backend",
                    descripcion="API",
                    publicada=True,
                ),
                usuario_actual_id=9,
            )

        service.repository.create.assert_not_called()

    def test_collaborator_cannot_edit_publish_or_unpublish_offers(self):
        service = self.offer_service_for_collaborator()
        service.repository.get_by_id.return_value = SimpleNamespace(
            id=7,
            empresa_id=3,
            publicada=True,
        )

        for publicada in (True, False):
            with self.subTest(publicada=publicada):
                with self.assertRaises(ForbiddenError):
                    service.update(
                        7,
                        UpdateOfertaDTO(publicada=publicada),
                        usuario_actual_id=9,
                    )

        service.repository.update.assert_not_called()

    def test_collaborator_cannot_access_private_offer_statistics(self):
        service = self.offer_service_for_collaborator()
        service.repository.get_by_id.return_value = SimpleNamespace(
            id=7,
            empresa_id=3,
            publicada=True,
        )

        with self.assertRaises(ForbiddenError):
            service.get_estadisticas(7, usuario_actual_id=9)

        service.postulacion_repository.count_grouped_by_estado.assert_not_called()

    def test_collaborator_cannot_manage_applications(self):
        service = PostulacionService(Mock())
        service.oferta_repository = Mock()
        service.oferta_repository.get_by_id.return_value = SimpleNamespace(
            id=7,
            empresa_id=3,
        )
        service.empresa_usuario_repository = Mock()
        service.empresa_usuario_repository.has_any_role.side_effect = allows(
            RolEmpresa.COLLABORATOR
        )
        service.repository = Mock()

        with self.assertRaises(ForbiddenError):
            service.get_by_oferta(7, usuario_actual_id=9)

        service.repository.get_by_oferta.assert_not_called()

    def test_collaborator_cannot_change_application_status(self):
        service = PostulacionService(Mock())
        service.repository = Mock()
        service.repository.get_by_id.return_value = SimpleNamespace(
            id=5,
            oferta_id=7,
            usuario_id=4,
            estado="entrevista",
        )
        service.oferta_repository = Mock()
        service.oferta_repository.get_by_id.return_value = SimpleNamespace(
            id=7,
            empresa_id=3,
        )
        service.empresa_usuario_repository = Mock()
        service.empresa_usuario_repository.has_any_role.side_effect = allows(
            RolEmpresa.COLLABORATOR
        )

        with self.assertRaises(ForbiddenError):
            service.update(
                5,
                UpdatePostulacionDTO(estado="contratado"),
                usuario_actual_id=9,
            )

        service.repository.update.assert_not_called()

    def test_owner_and_recruiter_keep_offer_and_application_permissions(self):
        for role in (RolEmpresa.OWNER, RolEmpresa.RECRUITER):
            with self.subTest(role=role):
                offer_service = OfertaService(Mock())
                offer_service.empresa_usuario_repository = Mock()
                offer_service.empresa_usuario_repository.has_any_role.side_effect = allows(
                    role
                )
                offer_service._requerir_gestor_empresa(3, 1)

                application_service = PostulacionService(Mock())
                application_service.empresa_usuario_repository = Mock()
                application_service.empresa_usuario_repository.has_any_role.side_effect = allows(
                    role
                )
                application_service._requerir_gestor_empresa(3, 1)


class AutomaticCollaboratorTests(unittest.TestCase):
    def hiring_service(
        self,
        existing_role: RolEmpresa | None = None,
        current_status: str = "entrevista",
    ):
        db = Mock()
        service = PostulacionService(db)
        offer = SimpleNamespace(
            id=7,
            empresa_id=3,
            titulo="Backend",
            publicada=True,
        )
        application = SimpleNamespace(
            id=5,
            oferta_id=7,
            usuario_id=9,
            estado=current_status,
            fecha=datetime.now(),
            oferta=offer,
        )
        service.repository = Mock()
        service.repository.get_by_id.return_value = application

        def update(model, data, *, commit=True):
            model.estado = data.estado
            return model

        service.repository.update.side_effect = update
        service.oferta_repository = Mock()
        service.oferta_repository.get_by_id.return_value = offer

        def update_offer(model, data, *, commit=True):
            model.publicada = data.publicada
            return model

        service.oferta_repository.update.side_effect = update_offer
        service.empresa_usuario_repository = Mock()
        service.empresa_usuario_repository.has_any_role.return_value = True
        service.empresa_usuario_repository.get_by_empresa_and_usuario.return_value = (
            None
            if existing_role is None
            else SimpleNamespace(
                empresa_id=3,
                usuario_id=9,
                rol=existing_role,
            )
        )
        service.notificacion_service = Mock()
        return service, db, application

    def test_hiring_creates_collaborator_in_the_same_transaction(self):
        service, db, _application = self.hiring_service()
        offer = service.oferta_repository.get_by_id.return_value

        result = service.update(
            5,
            UpdatePostulacionDTO(estado="contratado"),
            usuario_actual_id=1,
        )

        created = service.empresa_usuario_repository.create.call_args.args[0]
        self.assertEqual(created.empresa_id, 3)
        self.assertEqual(created.usuario_id, 9)
        self.assertEqual(created.rol, RolEmpresa.COLLABORATOR)
        self.assertFalse(
            service.empresa_usuario_repository.create.call_args.kwargs["commit"]
        )
        self.assertEqual(result.estado, "contratado")
        self.assertFalse(offer.publicada)
        updated_offer_data = service.oferta_repository.update.call_args.args[1]
        self.assertFalse(updated_offer_data.publicada)
        self.assertFalse(service.oferta_repository.update.call_args.kwargs["commit"])
        db.commit.assert_called_once_with()

    def test_hiring_an_already_unpublished_offer_is_idempotent(self):
        service, db, application = self.hiring_service()
        offer = service.oferta_repository.get_by_id.return_value
        offer.publicada = False

        result = service.update(
            5,
            UpdatePostulacionDTO(estado="contratado"),
            usuario_actual_id=1,
        )

        self.assertEqual(result.estado, "contratado")
        self.assertEqual(application.estado, "contratado")
        self.assertFalse(offer.publicada)
        service.oferta_repository.update.assert_called_once()
        db.commit.assert_called_once_with()

    def test_hiring_existing_collaborator_does_not_duplicate_membership(self):
        service, _db, application = self.hiring_service(RolEmpresa.COLLABORATOR)

        service.update(5, UpdatePostulacionDTO(estado="contratado"), 1)

        service.empresa_usuario_repository.create.assert_not_called()
        self.assertEqual(
            service.empresa_usuario_repository.get_by_empresa_and_usuario.return_value.rol,
            RolEmpresa.COLLABORATOR,
        )
        self.assertEqual(application.estado, "contratado")

    def test_hiring_owner_never_degrades_the_role(self):
        service, _db, _application = self.hiring_service(RolEmpresa.OWNER)

        service.update(5, UpdatePostulacionDTO(estado="contratado"), 1)

        service.empresa_usuario_repository.create.assert_not_called()
        self.assertEqual(
            service.empresa_usuario_repository.get_by_empresa_and_usuario.return_value.rol,
            RolEmpresa.OWNER,
        )

    def test_hiring_recruiter_never_degrades_the_role(self):
        service, _db, _application = self.hiring_service(RolEmpresa.RECRUITER)

        service.update(5, UpdatePostulacionDTO(estado="contratado"), 1)

        service.empresa_usuario_repository.create.assert_not_called()
        self.assertEqual(
            service.empresa_usuario_repository.get_by_empresa_and_usuario.return_value.rol,
            RolEmpresa.RECRUITER,
        )

    def test_later_status_attempt_never_removes_company_membership(self):
        service, _db, _application = self.hiring_service(
            RolEmpresa.COLLABORATOR,
            current_status="contratado",
        )

        with self.assertRaises(ConflictError):
            service.update(5, UpdatePostulacionDTO(estado="rechazada"), 1)

        service.empresa_usuario_repository.create.assert_not_called()
        service.empresa_usuario_repository.delete.assert_not_called()
        self.assertEqual(
            service.empresa_usuario_repository.get_by_empresa_and_usuario.return_value.rol,
            RolEmpresa.COLLABORATOR,
        )

    def test_notification_failure_rolls_back_hiring_and_membership(self):
        service, db, _application = self.hiring_service()
        service.notificacion_service.create_many.side_effect = RuntimeError(
            "notification failed"
        )

        with self.assertRaisesRegex(RuntimeError, "notification failed"):
            service.update(5, UpdatePostulacionDTO(estado="contratado"), 1)

        db.commit.assert_not_called()
        db.rollback.assert_called_once_with()
        self.assertFalse(
            service.oferta_repository.update.call_args.kwargs["commit"]
        )


if __name__ == "__main__":
    unittest.main()

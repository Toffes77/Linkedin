import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app  # noqa: F401 - registra todos los modelos SQLAlchemy
from src.db.connection import Base
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.oferta_model import Oferta
from src.db.models.usuario_model import Usuario
from src.dtos.oferta_dto import CreateOfertaDTO, UpdateOfertaDTO
from src.services.oferta_service import OfertaService


class OfferCreationAtomicityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        self.db: Session = self.SessionLocal()
        self.owner = Usuario(
            email="offer-owner@example.com",
            nombre="Offer owner",
            password_hash="not-used",
            headline="Owner",
            ciudad="Buenos Aires",
        )
        self.company = Empresa(nombre="Atomic offers")
        self.db.add_all([self.owner, self.company])
        self.db.flush()
        self.db.add(
            EmpresaUsuario(
                empresa_id=self.company.id,
                usuario_id=self.owner.id,
                rol=RolEmpresa.OWNER,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.query(Oferta).delete()
        self.db.query(EmpresaUsuario).delete()
        self.db.query(Empresa).delete()
        self.db.query(Usuario).delete()
        self.db.commit()
        self.db.close()

    def _create(self, *, publicada: bool):
        return OfertaService(self.db).create(
            CreateOfertaDTO(
                empresa_id=self.company.id,
                titulo="Backend",
                descripcion="API y PostgreSQL",
                publicada=publicada,
            ),
            self.owner.id,
        )

    def test_draft_creation_uses_one_commit_and_keeps_publication_date_empty(self):
        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            created = self._create(publicada=False)

        self.assertFalse(created.publicada)
        self.assertIsNone(created.fecha_publicacion)
        commit.assert_called_once_with()
        stored = self.db.get(Oferta, created.id)
        self.assertFalse(stored.publicada)
        self.assertIsNone(stored.fecha_publicacion)

    def test_published_creation_inserts_complete_state_with_one_commit(self):
        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            created = self._create(publicada=True)

        self.assertTrue(created.publicada)
        self.assertIsNotNone(created.fecha_publicacion)
        commit.assert_called_once_with()
        stored = self.db.get(Oferta, created.id)
        self.assertTrue(stored.publicada)
        self.assertEqual(stored.fecha_publicacion, created.fecha_publicacion)

    def test_failed_commit_does_not_leave_a_partially_created_offer(self):
        service = OfertaService(self.db)
        failure = IntegrityError("INSERT", {}, RuntimeError("forced failure"))
        with patch.object(self.db, "commit", side_effect=failure) as commit:
            with self.assertRaises(IntegrityError):
                service.create(
                    CreateOfertaDTO(
                        empresa_id=self.company.id,
                        titulo="Must rollback",
                        descripcion="No partial state",
                        publicada=True,
                    ),
                    self.owner.id,
                )

        commit.assert_called_once_with()
        self.db.rollback()
        self.assertIsNone(
            self.db.query(Oferta)
            .filter(Oferta.titulo == "Must rollback")
            .first()
        )

    def test_publish_and_unpublish_keep_existing_semantics(self):
        created = self._create(publicada=False)
        service = OfertaService(self.db)

        published = service.update(
            created.id,
            UpdateOfertaDTO(publicada=True),
            self.owner.id,
        )
        publication_date = published.fecha_publicacion
        self.assertTrue(published.publicada)
        self.assertIsNotNone(publication_date)

        unpublished = service.update(
            created.id,
            UpdateOfertaDTO(publicada=False),
            self.owner.id,
        )
        self.assertFalse(unpublished.publicada)
        self.assertEqual(unpublished.fecha_publicacion, publication_date)


if __name__ == "__main__":
    unittest.main()

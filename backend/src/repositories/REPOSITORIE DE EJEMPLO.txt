from sqlalchemy.orm import Session

from src.db.models.conductores_model import Conductores


class ConductoresRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, nombre: str, licencia: str, calificacion_promedio: float) -> Conductores:
        conductor = Conductores(nombre=nombre, licencia=licencia, calificacion_promedio=calificacion_promedio)
        self.db.add(conductor)
        self.db.commit()
        self.db.refresh(conductor)
        return conductor
    
    def get_by_id(self, conductor_id: int) -> Conductores | None:
        return self.db.query(Conductores).filter(Conductores.id == conductor_id).first()

    def update(self, conductor: Conductores) -> Conductores:
        self.db.add(conductor)
        self.db.commit()
        self.db.refresh(conductor)
        return conductor
    
    def delete(self, conductor: Conductores) -> None:
        self.db.delete(conductor)
        self.db.commit()

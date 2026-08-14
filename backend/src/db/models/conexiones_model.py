from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from db.connection import Base

class Conexion(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True)
    

    manda_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recibe_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    estado = Column(String(20), default="pendiente", nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    __table_args__ = (
    UniqueConstraint('manda_id', 'recibe_id', name='uq_manda_recibe'),
    CheckConstraint("estado IN ('pendiente', 'aceptado', 'rechazado')", name="check_valid_status"),
)
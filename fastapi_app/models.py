from sqlalchemy import Column, String, Float, BigInteger, Index
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Food(Base):
    __tablename__ = "foods"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    food_code = Column(String(20), unique=True, nullable=False)
    food_name = Column(String(200), nullable=False)
    data_type = Column(String(50), nullable=False)
    energy_kcal = Column(Float, nullable=True)
    water_g = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    carbohydrate_g = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    calcium_mg = Column(Float, nullable=True)
    sodium_mg = Column(Float, nullable=True)
    vitamin_c_mg = Column(Float, nullable=True)
    source_name = Column(String(200), nullable=True)

    __table_args__ = (
        Index("ix_foods_data_type", "data_type"),
        Index("ix_foods_energy_kcal", "energy_kcal"),
        Index("ix_foods_protein_g", "protein_g"),
    )

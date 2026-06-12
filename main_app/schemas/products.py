from pydantic import BaseModel, Field
from typing import Optional


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    img_path: Optional[str] = None
    category_id: int

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal


class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    stock: Literal["in-stock", "out-of-stock"]
    img_path: Optional[str]
    category_id: Optional[int]

    @field_validator("stock", mode="before")
    @classmethod
    def convert_stock_number_to_status(cls, value):
        if isinstance(value, str):
            return value

        return "in-stock" if value > 0 else "out-of-stock"

    model_config = ConfigDict(from_attributes=True)

class ProductStockResponse(BaseModel):
    id: int
    name: str
    stock: int
    img_path: Optional[str]
    category_id: Optional[int]

    class Config:
        from_attributes = True

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    img_path: Optional[str] = None
    category_id: Optional[int] = None
        
class ProductDeleteResponse(BaseModel):
    message: str
    # deleted_by: str
    deleted_product: ProductResponse
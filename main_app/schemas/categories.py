from typing import Optional, List
from pydantic import BaseModel, Field

class ProductInCategory(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, example="Bakery")
    description: Optional[str] = Field(None, max_length=500, example="A variety of baked goods including bread, pastries, and cakes.")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50, example="Bakery")
    description: Optional[str] = Field(None, max_length=500, example="Updated description")


class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True


class CategoryWithProducts(CategoryResponse):
    products: List[ProductInCategory] = []

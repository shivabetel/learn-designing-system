from pydantic import BaseModel
class BuyRequest(BaseModel):
    product_id: int
    user_id: str
    flash_sale_id: int
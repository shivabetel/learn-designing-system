from pydantic import BaseModel
class RestoreInventoryRequest(BaseModel):
    product_id: int
    flash_sale_id: int
    quantity: int
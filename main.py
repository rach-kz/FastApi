from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List, Optional
from database import products, carts, users
import uvicorn

app = FastAPI()

# Модели данных
class Product(BaseModel):
    id: int
    name: str
    description: str
    price: float

class CartItem(BaseModel):
    product_id: int
    email: str

class Order(BaseModel):
    email: str

class ProductUpdate(BaseModel):
    product_id: int
    price: Optional[float] = None
    description: Optional[str] = None

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float

# Аутентификация
security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    if username in users and users[username] == password:
        return username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )

# для клиентов
@app.get("/products", response_model=List[Product])
def get_products():
    return products

@app.post("/cart/add")
def add_to_cart(item: CartItem):
    product = next((p for p in products if p["id"] == item.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    carts.append(item.model_dump())  # Используем model_dump() вместо dict()
    return {"message": "Product added to cart"}

@app.post("/cart/remove")
def remove_from_cart(item: CartItem):
    cart_item = next((c for c in carts if c["product_id"] == item.product_id and c["email"] == item.email), None)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Product not found in cart")
    carts.remove(cart_item)
    return {"message": "Product removed from cart"}

@app.post("/order")
def place_order(order: Order):
    user_cart = [item for item in carts if item["email"] == order.email]
    if not user_cart:
        raise HTTPException(status_code=400, detail="Cart is empty")
    carts[:] = [item for item in carts if item["email"] != order.email]
    return {"message": "Order placed successfully"}

# для менеджеров и администраторов
@app.put("/product/update")
def update_product(update: ProductUpdate, username: str = Depends(authenticate)):
    if username not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    product = next((p for p in products if p["id"] == update.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if update.price:
        product["price"] = update.price
    if update.description:
        product["description"] = update.description
    return {"message": "Product updated successfully"}

@app.post("/product/add", status_code=status.HTTP_201_CREATED)
def add_product(product: ProductCreate, username: str = Depends(authenticate)):
    if username != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    new_product = {
        "id": len(products) + 1,
        "name": product.name,
        "description": product.description,
        "price": product.price,
    }
    products.append(new_product)
    return {"message": "Product added successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host='127.0.0.1', port=8000)
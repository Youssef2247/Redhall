# menu.py

MENU = {
    "🍔 Burgers": [
        {"id": "b1", "name": "Classic Burger",      "price": 45.00},
        {"id": "b2", "name": "Cheese Burger",        "price": 50.00},
        {"id": "b3", "name": "Crispy Chicken Burger","price": 55.00},
    ],
    "🍕 Pizza": [
        {"id": "p1", "name": "Margherita",           "price": 60.00},
        {"id": "p2", "name": "Pepperoni",            "price": 70.00},
        {"id": "p3", "name": "BBQ Chicken",          "price": 75.00},
    ],
    "🥤 Drinks": [
        {"id": "d1", "name": "Soft Drink",           "price": 15.00},
        {"id": "d2", "name": "Fresh Juice",          "price": 25.00},
        {"id": "d3", "name": "Water",                "price": 10.00},
    ],
    "🍟 Sides": [
        {"id": "s1", "name": "French Fries",         "price": 20.00},
        {"id": "s2", "name": "Onion Rings",          "price": 25.00},
        {"id": "s3", "name": "Coleslaw",             "price": 15.00},
    ],
}

def get_item_by_id(item_id: str):
    """Find a menu item by its ID across all categories."""
    for items in MENU.values():
        for item in items:
            if item["id"] == item_id:
                return item
    return None
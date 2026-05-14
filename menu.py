# menu.py

MENU = {
    "🍔 Burgers & Hotdog sandwiches": [
        {"id": "b1", "name": "Classic Burger , برجر سادة",      "price": 30.00},
        {"id": "b2", "name": "Cheese Burger , برجر جبنة",        "price": 40.00},
        {"id": "b3", "name": "Classic Hotdog, هوت دوج ","price": 35.00},
        {"id": "b4", "name": "Hotdog with cheese, هوت دوج بالجبنة","price": 45.00},
        {"id": "b5", "name": "Classic Sausages, سدق","price": 30.00},
        {"id": "b6", "name": "Sausages with cheese, سدق بالجبنة","price": 40.00},
    ],
    "🍕 chicken": [
        {"id": "p1", "name": "Strips , ستريبس",           "price": 55.00},
        {"id": "p2", "name": "Grilled Chicken, فراخ مشوية",            "price": 50.00},
        {"id": "p3", "name": "Fajita , فاهيتا  ",          "price": 45.00},
        {"id": "p4", "name": "Fajita with cheese,فاهيتا بالجبنة  ",          "price": 55.00},
        {"id": "p5", "name": "Shish Tawook , شيش طاووق  ",          "price": 45.00},
        {"id": "p6", "name": "Shish Tawook with cheese , شيش طاووق بالجبنة  ",          "price": 55.00},
    ],
    "🥤 Drinks": [
        {"id": "d1", "name": "Soft Drink",           "price": 15.00},
        {"id": "d2", "name": "Fresh Juice",          "price": 25.00},
        {"id": "d3", "name": "Water",                "price": 10.00},
    ],
    "🍟Fries & Fried Cheese": [
        {"id": "s1", "name": "French Fries Sandwich, ساندوتش بطاطس ",         "price": 30.00},
        {"id": "s2", "name": "Fried Cheese, جبنة مقلية",          "price": 20.00},
    ],
}

def get_item_by_id(item_id: str):
    """Find a menu item by its ID across all categories."""
    for items in MENU.values():
        for item in items:
            if item["id"] == item_id:
                return item
    return None

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
    "🥤 Coffee & Drinks": [
        {"id": "d1", "name": "Latte, لاتيه",           "price": 33.00},
        {"id": "d2", "name": "Espresso, إسبريسو",          "price": 20.00},
        {"id": "d3", "name": "Double Espresso, دابل إسبريسو ",          "price": 40.00},
        {"id": "d4", "name": "American, امريكان",          "price": 20.00},
        {"id": "d5", "name": "Macchiato, ميكاتو",          "price": 25.00},
        {"id": "d6", "name": "Flat White, فلات وايت",          "price": 25.00},
        {"id": "d7", "name": "Cappuccino, كابتشينو",          "price": 37.00},
        {"id": "d8", "name": "Nescafe Caramel, نسكافيه كاراميل",          "price": 35.00},
        {"id": "d9", "name": "Moccha, موكا",          "price": 42.00},
        {"id": "d10", "name": "Hot Chocolate, هوت تشوكليت",          "price": 35.00},
        {"id": "11", "name": "Milk, لبن",          "price": 20.00},
        {"id": "d12", "name": "Tea with Milk, شاي بلبن",          "price": 20.00},
        {"id": "d13", "name": "Tea, شاي",          "price": 10.00},
        {"id": "d14", "name": "French Coffee, قهوة فرنساوي",          "price": 25.00},
        {"id": "15", "name": "Water",                "price": 10.00},
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

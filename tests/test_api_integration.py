import sqlite3

import pytest
import requests

BASE_URL = "https://dummyjson.com"  # API publica de prueba (carrito simulado, no persiste)
T = 10


@pytest.fixture
def db_connection():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE carrito (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            cantidad INTEGER NOT NULL,
            total REAL NOT NULL)"""
    )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def producto():
    r = requests.get(f"{BASE_URL}/products/1", timeout=T)
    assert r.status_code == 200
    return r.json()


def agregar(conn, p, cantidad):
    """Regla de negocio: cantidad entera, > 0 y <= stock. Guarda y devuelve el total."""
    if type(cantidad) is not int or cantidad <= 0:
        raise ValueError("cantidad invalida")
    if cantidad > p["stock"]:
        raise ValueError("sin stock")
    total = round(p["price"] * cantidad, 2)
    conn.execute(
        "INSERT INTO carrito (producto_id, nombre, precio, cantidad, total) VALUES (?,?,?,?,?)",
        (p["id"], p["title"], p["price"], cantidad, total),
    )
    conn.commit()
    return total


def resumen(conn):
    return conn.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM carrito").fetchone()


def test_consultar_productos():
    r = requests.get(f"{BASE_URL}/products?limit=5", timeout=T)
    assert r.status_code == 200
    products = r.json()["products"]
    assert isinstance(products, list) and len(products) > 0
    assert {"id", "title", "price"} <= products[0].keys()


def test_contrato_estricto(producto):
    assert type(producto["id"]) is int
    assert type(producto["title"]) is str
    assert type(producto["price"]) in (int, float)
    assert type(producto["category"]) is str
    assert type(producto["thumbnail"]) is str  # DummyJSON usa 'thumbnail' en vez de 'image'


def test_tiempo_respuesta():
    ms = [requests.get(f"{BASE_URL}/products?limit=5", timeout=T).elapsed.total_seconds() * 1000
          for _ in range(3)]
    assert sum(ms) / 3 < 1000


def test_producto_inexistente(db_connection):
    r = requests.get(f"{BASE_URL}/products/999999", timeout=T)
    assert r.status_code == 404
    assert "message" in r.json()
    assert resumen(db_connection) == (0, 0)  # no se inserta nada


def test_insertar_producto(db_connection, producto):
    agregar(db_connection, producto, 2)
    assert resumen(db_connection) == (1, round(producto["price"] * 2, 2))


def test_total_carrito(db_connection, producto):
    agregar(db_connection, producto, 1)
    agregar(db_connection, producto, 3)
    n, total = resumen(db_connection)
    assert n == 2 and total == pytest.approx(producto["price"] * 4)


@pytest.mark.parametrize("cantidad", [0, -1, "2", 1.5, 10**6])
def test_cantidades_invalidas(db_connection, producto, cantidad):
    with pytest.raises(ValueError):
        agregar(db_connection, producto, cantidad)
    assert resumen(db_connection) == (0, 0)


def test_idempotencia(db_connection, producto):
    # Hallazgo: sin clave de idempotencia, repetir la operacion duplica filas.
    agregar(db_connection, producto, 1)
    agregar(db_connection, producto, 1)
    assert resumen(db_connection)[0] == 2


@pytest.mark.parametrize("body", [{}, {"userId": 1}, {"userId": 1, "products": "x"}])
def test_body_invalido(body):
    r = requests.post(f"{BASE_URL}/carts/add", json=body, timeout=T)
    assert 400 <= r.status_code < 500
    assert "message" in r.json()  # error claro, documentar el texto recibido


def test_carrito_api_total(producto):
    body = {"userId": 1, "products": [{"id": producto["id"], "quantity": 2}]}
    r = requests.post(f"{BASE_URL}/carts/add", json=body, timeout=T)
    assert r.status_code == 201
    cart = r.json()
    assert cart["products"][0]["quantity"] == 2
    assert cart["total"] == pytest.approx(producto["price"] * 2)


def test_autenticacion_con_y_sin_token():
    cred = {"username": "emilys", "password": "emilyspass"}  # usuario demo publico de DummyJSON
    login = requests.post(f"{BASE_URL}/auth/login", json=cred, timeout=T)
    assert login.status_code == 200
    token = login.json()["accessToken"]
    con = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=T)
    sin = requests.get(f"{BASE_URL}/auth/me", timeout=T)
    assert con.status_code == 200
    assert sin.status_code == 401


def test_bd_falla_api_ok(db_connection, producto):
    # La API responde bien (fixture) pero la BD falla: debe haber error controlado, sin exito falso.
    db_connection.execute("DROP TABLE carrito")
    with pytest.raises(sqlite3.OperationalError):
        agregar(db_connection, producto, 1)

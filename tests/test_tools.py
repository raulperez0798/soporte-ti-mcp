import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server import buscar_incidente, consultar_estado_ticket, crear_borrador_ticket


def test_buscar_incidente_encuentra_resultado():
    resultado = buscar_incidente("vpn")
    assert len(resultado["resultados"]) >= 1


def test_buscar_incidente_sin_resultado():
    resultado = buscar_incidente("algo_que_no_existe")
    assert resultado["resultados"] == []


def test_buscar_incidente_vacio_devuelve_error():
    resultado = buscar_incidente("")
    assert "error" in resultado


def test_consultar_estado_ticket_existente():
    resultado = consultar_estado_ticket("TCK-1001")
    assert resultado["estado"] == "abierto"


def test_consultar_estado_ticket_inexistente():
    resultado = consultar_estado_ticket("TCK-9999")
    assert "error" in resultado


def test_crear_borrador_ticket():
    resultado = crear_borrador_ticket("Pantalla negra", "El monitor no enciende", "hardware")
    assert resultado["estado"] == "borrador"
    assert resultado["ticket_id"].startswith("TCK-")


def test_crear_borrador_ticket_sin_datos():
    resultado = crear_borrador_ticket("", "", "")
    assert "error" in resultado

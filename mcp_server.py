"""Servidor MCP del asistente de soporte TI.

Expone tres tools de negocio sobre datos simulados en memoria:
buscar_incidente, consultar_estado_ticket y crear_borrador_ticket.

Transporte configurable via MCP_TRANSPORT:
- "stdio" (por defecto): para Claude Desktop u otro host que administre
  el proceso localmente.
- "streamable-http": para desplegar el MCP como servicio remoto propio,
  consultado por la app Streamlit via MCP_SERVER_URL.
"""
import os

from fastmcp import FastMCP

mcp = FastMCP("soporte-ti")

INCIDENTES = [
    {
        "id": "INC-001",
        "titulo": "VPN no conecta",
        "categoria": "red",
        "estado": "conocido",
        "solucion": "Reiniciar el cliente VPN y verificar usuario y contrasena.",
    },
    {
        "id": "INC-002",
        "titulo": "Impresora no imprime",
        "categoria": "hardware",
        "estado": "conocido",
        "solucion": "Reinstalar el driver de la impresora desde el portal interno.",
    },
    {
        "id": "INC-003",
        "titulo": "Correo no sincroniza",
        "categoria": "software",
        "estado": "conocido",
        "solucion": "Verificar espacio del buzon y reiniciar el cliente de correo.",
    },
    {
        "id": "INC-004",
        "titulo": "Sistema de facturacion caido",
        "categoria": "aplicacion",
        "estado": "en_investigacion",
        "solucion": "Equipo de infraestructura reiniciando el servicio, sin ETA aun.",
    },
]

# Datos simulados; crear_borrador_ticket agrega entradas aqui durante la sesion.
TICKETS = {
    "TCK-1001": {
        "estado": "abierto",
        "prioridad": "alta",
        "asignado": "Soporte N1",
        "ultima_actualizacion": "2026-08-05",
    },
    "TCK-1002": {
        "estado": "cerrado",
        "prioridad": "baja",
        "asignado": "Soporte N1",
        "ultima_actualizacion": "2026-08-01",
    },
    "TCK-1003": {
        "estado": "en_progreso",
        "prioridad": "media",
        "asignado": "Soporte N2",
        "ultima_actualizacion": "2026-08-07",
    },
}


@mcp.tool()
def buscar_incidente(palabra_clave: str) -> dict:
    """Busca incidentes conocidos por palabra clave en el titulo o la categoria."""
    if not palabra_clave or not palabra_clave.strip():
        return {"error": "palabra_clave no puede estar vacia", "resultados": []}
    q = palabra_clave.lower().strip()
    resultados = [
        i for i in INCIDENTES if q in i["titulo"].lower() or q in i["categoria"].lower()
    ]
    return {"resultados": resultados}


@mcp.tool()
def consultar_estado_ticket(ticket_id: str) -> dict:
    """Devuelve el estado, prioridad y responsable de un ticket existente."""
    if not ticket_id or not ticket_id.strip():
        return {"error": "ticket_id no puede estar vacio"}
    ticket = TICKETS.get(ticket_id.strip().upper())
    if not ticket:
        return {"error": f"No existe el ticket {ticket_id}"}
    return {"ticket_id": ticket_id.strip().upper(), **ticket}


@mcp.tool()
def crear_borrador_ticket(titulo: str, descripcion: str, categoria: str) -> dict:
    """Crea un borrador de ticket nuevo a partir de un problema reportado por el colaborador."""
    if not titulo or not titulo.strip() or not descripcion or not descripcion.strip():
        return {"error": "titulo y descripcion son obligatorios"}
    nuevo_id = f"TCK-{1000 + len(TICKETS) + 1}"
    TICKETS[nuevo_id] = {
        "estado": "borrador",
        "prioridad": "por_definir",
        "asignado": "sin_asignar",
        "ultima_actualizacion": "recien_creado",
        "titulo": titulo.strip(),
        "descripcion": descripcion.strip(),
        "categoria": categoria.strip() if categoria else "sin_categoria",
    }
    return {"ticket_id": nuevo_id, "estado": "borrador"}


if __name__ == "__main__":
    transporte = os.environ.get("MCP_TRANSPORT", "stdio")
    if transporte == "streamable-http":
        puerto = int(os.environ.get("PORT", 8000))
        # stateless_http evita depender de sesiones pegadas a una conexion,
        # mas confiable detras de proxies como Render (ver README).
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=puerto,
            stateless_http=True,
        )
    else:
        mcp.run()

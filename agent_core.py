"""Agente LangChain + OpenAI conectado al servidor MCP de soporte TI.

Si la variable de entorno MCP_SERVER_URL esta configurada, el agente se
conecta al MCP como servicio remoto por streamable-http (arquitectura
recomendada para produccion). Si no esta configurada, levanta el MCP como
subproceso local via stdio (mas simple para correr todo en un solo lugar
durante desarrollo).
"""
import os
import sys
import asyncio

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver

# Ventana de memoria: cuando la conversacion supera 10 mensajes, se resumen
# los mas viejos y se conservan los ultimos 6 tal cual (ver README, seccion Memoria).
VENTANA_TRIGGER = ("messages", 10)
VENTANA_KEEP = ("messages", 6)

load_dotenv()

MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "mcp_server.py")

SYSTEM_PROMPT = """
Eres un agente de soporte TI que ayuda a colaboradores internos.
Tu alcance es unicamente: buscar incidentes conocidos, consultar el estado de
tickets y crear borradores de tickets nuevos, usando siempre las tools.
Cuando el colaborador describa un problema (por ejemplo "no me anda la
impresora" o "tengo problemas con la VPN"), llama primero a
buscar_incidente con una palabra clave relevante antes de pedir mas
detalles. Solo pide una aclaracion si la busqueda no devuelve resultados
utiles o si falta un dato indispensable (por ejemplo un ticket_id para
consultar_estado_ticket).
No inventes ids de ticket, estados ni soluciones que no vengan de una tool.
Si la pregunta no tiene relacion con soporte TI (incidentes o tickets),
no la respondas con conocimiento general: indica amablemente que esta
fuera de tu alcance y que solo puedes ayudar con soporte TI.
Al final de tu respuesta indica brevemente que evidencia usaste.
"""

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "").strip()

if MCP_SERVER_URL:
    _client = MultiServerMCPClient(
        {
            "soporte-ti": {
                "url": MCP_SERVER_URL.rstrip("/") + "/mcp",
                "transport": "streamable_http",
            }
        }
    )
else:
    _client = MultiServerMCPClient(
        {
            "soporte-ti": {
                "command": sys.executable,
                "args": [MCP_SERVER_PATH],
                "transport": "stdio",
            }
        }
    )

_memory = InMemorySaver()
_agent = None


async def _get_agent():
    global _agent
    if _agent is None:
        tools = await _client.get_tools()
        model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-5.4-nano"), temperature=0)
        _agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=_memory,
            middleware=[
                SummarizationMiddleware(
                    model=model,
                    trigger=VENTANA_TRIGGER,
                    keep=VENTANA_KEEP,
                )
            ],
        )
    return _agent


async def _run(mensaje: str, session_id: str) -> dict:
    agent = await _get_agent()
    config = {"configurable": {"thread_id": session_id}}
    resultado = await agent.ainvoke(
        {"messages": [{"role": "user", "content": mensaje}]},
        config=config,
    )
    ultimo = resultado["messages"][-1]
    trace = [
        {"tipo": type(m).__name__, "contenido": getattr(m, "content", "")}
        for m in resultado["messages"]
    ]
    return {"answer": ultimo.content, "trace": trace}


def run_agent(mensaje: str, session_id: str) -> dict:
    """Punto de entrada sincrono usado por la interfaz de Streamlit."""
    return asyncio.run(_run(mensaje, session_id))

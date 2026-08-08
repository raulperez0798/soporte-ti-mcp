# Asistente de Soporte TI

Agente construido con LangChain + OpenAI que consulta un servidor MCP propio
para ayudar a colaboradores internos con temas de soporte TI.

## Problema

**Usuario:** colaborador interno de la empresa.
**Necesidad:** resolver dudas rapidas de soporte TI sin abrir un ticket manual
cada vez: revisar si un problema ya es un incidente conocido, ver en que
estado esta un ticket existente, o dejar creado un borrador de ticket nuevo.
**Que no cubre:** no reemplaza al equipo de soporte, no ejecuta cambios reales
en un sistema de tickets externo (los tickets se guardan en memoria durante
la sesion) y no resuelve incidentes fuera del catalogo simulado.

**Flujo tipico:** el colaborador escribe su problema en el chat ("tengo
problemas con la VPN"), el agente busca en el catalogo de incidentes y
responde con la solucion conocida; si el colaborador pregunta por un ticket
especifico el agente consulta su estado; si el problema no tiene incidente
conocido, el agente ofrece crear un borrador de ticket con titulo,
descripcion y categoria.

## Arquitectura

```
Usuario -> Streamlit (chat) -> Agente LangChain + OpenAI -> MCP client (stdio)
                                                                    |
                                                          Servidor MCP propio
                                                       (mcp_server.py, datos en memoria)
```

El servidor MCP se levanta como subproceso de la propia app (transporte
stdio), por lo que no requiere un despliegue ni un `MCP_SERVER_URL` separado.

## Tools MCP

| Tool | Proposito | Entrada | Validacion | Salida | Riesgo |
|---|---|---|---|---|---|
| `buscar_incidente` | Busca incidentes conocidos por palabra clave | `palabra_clave: str` | Rechaza vacio/solo espacios | `{resultados: [...]}` | Lectura, bajo riesgo |
| `consultar_estado_ticket` | Devuelve estado, prioridad y responsable de un ticket | `ticket_id: str` | Rechaza vacio; valida que el ticket exista | `{ticket_id, estado, prioridad, asignado, ultima_actualizacion}` | Lectura, bajo riesgo |
| `crear_borrador_ticket` | Crea un borrador de ticket nuevo | `titulo: str, descripcion: str, categoria: str` | Rechaza titulo o descripcion vacios | `{ticket_id, estado: "borrador"}` | Escritura, riesgo medio (solo crea un borrador, no notifica ni asigna) |

Las tres devuelven un `{"error": ...}` estructurado ante entrada invalida en
vez de lanzar una excepcion opaca (ver `tests/test_tools.py`).

## Memoria

Cada sesion de Streamlit genera un `session_id` propio (mostrado en la barra
lateral) que se usa como `thread_id` del `InMemorySaver` de LangGraph. Esto
permite que el agente resuelva referencias como "ese ticket" en un segundo
mensaje sin repetir el identificador. La memoria vive solo en el proceso: se
pierde si la app se reinicia, y se puede limpiar manualmente con el boton
"Reiniciar conversacion".

**Ventana:** para no mandar el historial completo al modelo en conversaciones
largas, se usa `SummarizationMiddleware` de LangChain (`agent_core.py`): al
superar 10 mensajes en la sesion, los mas antiguos se condensan en un resumen
y se conservan los ultimos 6 mensajes tal cual. Esto cubre tanto la ventana
como el resumen que menciona la guia, sin perder el contexto relevante.

## Instalacion local

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # completar OPENAI_API_KEY
streamlit run app_streamlit.py
```

## Pruebas

```bash
pytest -q
```

`tests/test_tools.py` prueba las tres tools directamente (casos validos,
inexistentes y de entrada invalida).

## Evidencia: agente + memoria en accion

Consulta directa (usa `buscar_incidente`):

```
Usuario: Tengo problemas con la VPN, hay algun incidente conocido?

[tool_call] buscar_incidente(palabra_clave="VPN")
[tool_result] {"resultados": [{"id": "INC-001", "titulo": "VPN no conecta",
  "categoria": "red", "estado": "conocido",
  "solucion": "Reiniciar el cliente VPN y verificar usuario y contrasena."}]}

Agente: He encontrado un incidente conocido relacionado con la VPN:
- Titulo: VPN no conecta
- Categoria: Red
- Estado: Conocido
- Solucion: Reiniciar el cliente VPN y verificar usuario y contrasena.
Evidencia utilizada: busqueda de incidentes conocidos por la palabra clave "VPN".
```

Referencia con memoria (mismo `session_id`, dos turnos, usa `consultar_estado_ticket`):

```
Usuario: Revisa el ticket TCK-1001
Agente: [consulta la tool y responde estado: abierto, prioridad: alta, ...]

Usuario: Cual es la prioridad de ese ticket?
Agente: La prioridad del ticket TCK-1001 es alta.
Evidencia utilizada: Consulte el estado del ticket TCK-1001.
```

El agente resuelve "ese ticket" sin que el usuario repita el identificador,
gracias al `thread_id` compartido en la sesion.

## Despliegue en Streamlit Community Cloud

1. Sube el repo a GitHub (ver comandos abajo).
2. En https://share.streamlit.io -> "Create app" -> conecta el repo, rama
   `main` y archivo de entrada `app_streamlit.py`.
3. En "Secrets" agrega:
   ```
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-4o-mini"
   ```
4. Deploy. Prueba la URL publica con los 5 escenarios (consulta directa,
   compuesta, referencia con memoria, dato inexistente, fuera de alcance).

## Enlaces

- App: https://soporte-ti-mcp-ah3o2jvewufpghg4tdtc9w.streamlit.app/
- Repositorio: https://github.com/raulperez0798/soporte-ti-mcp

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
Usuario -> Streamlit (chat) -> Agente LangChain + OpenAI -> MCP client (streamable-http)
                                                                    |
                                                          Servidor MCP propio
                                                (mcp_server.py, remoto, datos en memoria)

Modo local adicional:
Claude Desktop --stdio--> mcp_server.py (mismo codigo, otro transporte)
```

Se sigue la arquitectura de despliegue recomendada por la guia: Streamlit
publica solo el frontend y el servidor MCP corre como **servicio remoto
independiente**, consultado via HTTP mediante la variable `MCP_SERVER_URL`.
Esto evita depender de un proceso local dentro de la app alojada.

El transporte del MCP es configurable con la variable `MCP_TRANSPORT`
(`mcp_server.py`):
- `streamable-http` (usada en el servicio remoto desplegado).
- `stdio` (por defecto), usada por Claude Desktop o para correr todo en un
  solo proceso durante desarrollo local sin desplegar nada extra.

`agent_core.py` elige automaticamente como conectarse: si `MCP_SERVER_URL`
esta configurada se conecta por HTTP a ese endpoint; si no, levanta
`mcp_server.py` como subproceso local via stdio. Esto permite desarrollar y
probar todo en una sola maquina sin perder la opcion de desplegar el MCP
como servicio separado.

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

Sin configurar `MCP_SERVER_URL`, la app levanta el MCP como subproceso local
(stdio) automaticamente: no hace falta correr nada mas para desarrollar.

Para probar el modo remoto en local (el mismo que usa produccion):

```bash
# Terminal 1: levantar el MCP en modo HTTP
MCP_TRANSPORT=streamable-http PORT=8000 python mcp_server.py

# Terminal 2: apuntar la app a ese MCP
echo "MCP_SERVER_URL=http://localhost:8000" >> .env
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

## Despliegue

Son dos servicios: el MCP (backend) en Render y la interfaz en Streamlit
Community Cloud, ambos apuntando al mismo repositorio de GitHub.

### 1. Servidor MCP en Render (servicio HTTP remoto)

1. Sube el repo a GitHub (ver comandos mas abajo).
2. En https://render.com -> "New +" -> "Web Service" -> conecta el repo.
3. Configura:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python mcp_server.py`
   - **Variables de entorno:** `MCP_TRANSPORT=streamable-http`
     (Render inyecta `PORT` automaticamente).
4. Deploy. Copia la URL publica que te da Render, por ejemplo
   `https://soporte-ti-mcp.onrender.com`.

En el free tier, el servicio se duerme tras un rato sin uso y la primera
consulta tras dormirse tarda unos segundos extra en responder (cold start).

### 2. Interfaz en Streamlit Community Cloud

1. En https://share.streamlit.io -> "Create app" -> conecta el mismo repo,
   rama `main` y archivo de entrada `app_streamlit.py`.
2. En "Secrets" agrega:
   ```
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-5.4-nano"
   MCP_SERVER_URL = "https://soporte-ti-mcp.onrender.com"
   ```
3. Deploy. Prueba la URL publica con los 5 escenarios (consulta directa,
   compuesta, referencia con memoria, dato inexistente, fuera de alcance).

## Configuracion local para Claude Desktop

Como evidencia adicional de que el MCP no fue creado solo para Streamlit,
puede conectarse a Claude Desktop en modo local (stdio). Copia
`claude_desktop_config.example.json` a la configuracion de Claude Desktop
(`claude_desktop_config.json`), ajustando la ruta absoluta:

```json
{
  "mcpServers": {
    "soporte-ti": {
      "command": "python",
      "args": ["/ruta/absoluta/a/mcp_server.py"]
    }
  }
}
```

Sin `MCP_TRANSPORT` configurado, `mcp_server.py` usa stdio por defecto, que
es lo que Claude Desktop espera al administrar el proceso directamente. Esta
demostracion es complementaria; el entregable obligatorio sigue siendo el
enlace de Streamlit y el repositorio de GitHub.

## Enlaces

- App: https://soporte-ti-mcp-ah3o2jvewufpghg4tdtc9w.streamlit.app/
- Repositorio: https://github.com/raulperez0798/soporte-ti-mcp
- Servidor MCP: https://soporte-ti-mcp-xx9m.onrender.com

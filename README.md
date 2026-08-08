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

| Tool | Proposito | Entrada | Salida |
|---|---|---|---|
| `buscar_incidente` | Busca incidentes conocidos por palabra clave | `palabra_clave: str` | `{resultados: [...]}` |
| `consultar_estado_ticket` | Devuelve estado, prioridad y responsable de un ticket | `ticket_id: str` | `{ticket_id, estado, prioridad, asignado, ultima_actualizacion}` |
| `crear_borrador_ticket` | Crea un borrador de ticket nuevo | `titulo: str, descripcion: str, categoria: str` | `{ticket_id, estado: "borrador"}` |

Las tres validan entradas vacias/invalidas y devuelven un `{"error": ...}`
estructurado en vez de lanzar una excepcion opaca.

## Memoria

Cada sesion de Streamlit genera un `session_id` propio (mostrado en la barra
lateral) que se usa como `thread_id` del `InMemorySaver` de LangGraph. Esto
permite que el agente resuelva referencias como "ese ticket" en un segundo
mensaje sin repetir el identificador. La memoria vive solo en el proceso: se
pierde si la app se reinicia, y se puede limpiar manualmente con el boton
"Reiniciar conversacion".

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

- App: https://... (completar tras el despliegue)
- Repositorio: https://github.com/... (completar tras subir a GitHub)

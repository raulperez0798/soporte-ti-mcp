import os
import uuid

import streamlit as st

try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ.setdefault("OPENAI_API_KEY", st.secrets["OPENAI_API_KEY"])
    if "OPENAI_MODEL" in st.secrets:
        os.environ.setdefault("OPENAI_MODEL", st.secrets["OPENAI_MODEL"])
    if "MCP_SERVER_URL" in st.secrets:
        os.environ.setdefault("MCP_SERVER_URL", st.secrets["MCP_SERVER_URL"])
except Exception:
    pass

from agent_core import run_agent

st.set_page_config(page_title="Asistente de Soporte TI", layout="wide")
st.title("Asistente de Soporte TI")
st.caption(
    "Agente para colaboradores: busca incidentes conocidos, consulta el estado "
    "de tickets y crea borradores de tickets nuevos."
)

if "session_id" not in st.session_state:
    st.session_state.session_id = "sesion-" + str(uuid.uuid4())[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Estado de la sesion")
    st.code(st.session_state.session_id)
    if st.button("Reiniciar conversacion"):
        st.session_state.session_id = "sesion-" + str(uuid.uuid4())[:8]
        st.session_state.messages = []
        st.rerun()

    st.subheader("Que puede hacer")
    st.markdown(
        "- Buscar incidentes conocidos (ej: VPN, impresora, correo)\n"
        "- Consultar el estado de un ticket (ej: TCK-1001)\n"
        "- Crear un borrador de ticket nuevo"
    )

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])

if prompt := st.chat_input("Escribe tu consulta de soporte TI..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not os.getenv("OPENAI_API_KEY"):
            error_msg = "Falta configurar OPENAI_API_KEY (ver .env o secrets de Streamlit)."
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        else:
            try:
                with st.spinner("Consultando al agente..."):
                    resultado = run_agent(prompt, st.session_state.session_id)
                st.markdown(resultado["answer"])
                with st.expander("Evidencia y tools usadas"):
                    st.json(resultado["trace"])
                st.session_state.messages.append(
                    {"role": "assistant", "content": resultado["answer"]}
                )
            except Exception as e:
                error_msg = f"Ocurrio un error al consultar el agente: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

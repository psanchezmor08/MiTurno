import streamlit as st
import pandas as pd
from langchain_community.llms import Ollama
import json
import re
import os

st.set_page_config(page_title="MiTurno IA Local", layout="wide")

ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stDataFrame { background-color: white; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🗓️ MiTurno IA: Puerto 8505")

with st.sidebar:
    st.header("Configuración")
    modelo = st.selectbox("IA", ["llama3", "mistral"])
    empleados = st.text_area("Lista de Empleados", "Juan, Maria, Pedro, Ana, Luis")
    reglas = st.text_area("Reglas y Turnos", 
                           "Turnos: Mañana (M), Tarde (T). Cada uno libra 2 días. No trabajar tarde y luego mañana.")

if st.button("🚀 Generar Cuadrante"):
    try:
        llm = Ollama(model=modelo, base_url=ollama_host)
        
        prompt = f"""
        Genera un cuadrante semanal JSON para: {empleados}.
        Reglas: {reglas}.
        Responde SOLO un JSON con este formato:
        {{"Nombre": ["M", "T", "L", "M", "T", "L", "M"]}}
        (L=Libre).
        """
        
        with st.spinner("IA calculando..."):
            response = llm.invoke(prompt)
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                df = pd.DataFrame.from_dict(data, orient='index', 
                                         columns=["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"])
                
                def style_cells(val):
                    if val == 'M': color = '#dcfce7'
                    elif val == 'T': color = '#fef9c3'
                    elif val == 'L': color = '#fee2e2'
                    else: color = '#f1f5f9'
                    return f'background-color: {color}'

                st.dataframe(df.style.applymap(style_cells), use_container_width=True)
                st.download_button("Descargar CSV", df.to_csv(), "cuadrante.csv")
            else:
                st.error("Error en formato. Reintenta.")
    except Exception as e:
        st.error(f"Error: {e}")

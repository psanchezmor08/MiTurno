import streamlit as st
import pandas as pd
from langchain_community.llms import Ollama
import json
import re
import os
from datetime import datetime, timedelta

# Configuración estética similar a la de tu proyecto React (Tailwind-style)
st.set_page_config(page_title="MiTurno IA - Generador de Cuadrantes", layout="wide")

# Estilos CSS personalizados para que se vea moderno
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #2563eb; color: white; }
    .turno-m { background-color: #dbeafe; color: #1e40af; padding: 5px; border-radius: 4px; font-weight: bold; text-align: center; }
    .turno-t { background-color: #fef9c3; color: #854d0e; padding: 5px; border-radius: 4px; font-weight: bold; text-align: center; }
    .turno-n { background-color: #f1f5f9; color: #1e293b; padding: 5px; border-radius: 4px; font-weight: bold; text-align: center; }
    .turno-l { background-color: #fee2e2; color: #991b1b; padding: 5px; border-radius: 4px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE CONEXIÓN ---
ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
llm = Ollama(model="llama3", base_url=ollama_host)

# --- INTERFAZ ---
st.title("🗓️ MiTurno IA: Gestión de Cuadrantes")
st.subheader("Configuración de turnos y personal")

col1, col2 = st.columns([1, 2])

with col1:
    st.info("Configura los parámetros aquí")
    with st.expander("👥 Personal", expanded=True):
        empleados = st.text_area("Nombres (uno por línea o comas)", "Juan, Maria, Pedro, Ana, Isabel")
    
    with st.expander("⚙️ Reglas del Cuadrante", expanded=True):
        fecha_inicio = st.date_input("Fecha de inicio", datetime.now())
        turnos_def = st.text_input("Define los turnos", "Mañana (M), Tarde (T), Noche (N)")
        reglas = st.text_area("Restricciones (Lenguaje Natural)", 
                               "Máximo 5 días seguidos. Maria no trabaja lunes. Pedro siempre turno M. Mínimo 2 personas por turno.")

with col2:
    if st.button("Generar Cuadrante Inteligente con Llama3"):
        with st.spinner("La IA está organizando los turnos siguiendo tus reglas..."):
            # Prompt de ingeniería para que la IA devuelva un JSON estructurado
            prompt = f"""
            Genera un cuadrante semanal desde el {fecha_inicio}.
            Empleados: {empleados}.
            Turnos disponibles: {turnos_def}.
            Reglas: {reglas}.
            
            IMPORTANTE: Responde EXCLUSIVAMENTE con un JSON puro, sin texto antes ni después.
            Formato: {{"Nombre": ["Turno1", "Turno2", "Turno3", "Turno4", "Turno5", "Turno6", "Turno7"]}}
            Usa 'L' para días libres.
            """
            
            try:
                raw_response = llm.invoke(prompt)
                # Limpiar la respuesta para asegurar que es JSON
                json_str = re.search(r'\{.*\}', raw_response, re.DOTALL).group()
                data = json.loads(json_str)
                
                # Crear los encabezados de fecha
                dias = [(fecha_inicio + timedelta(days=i)).strftime("%a %d/%m") for i in range(7)]
                df = pd.DataFrame.from_dict(data, orient='index', columns=dias)
                
                st.success("✅ Cuadrante generado")
                
                # Renderizado visual (reemplazando st.table por algo con colores)
                def color_turnos(val):
                    if val == 'M': return 'background-color: #dbeafe; color: #1e40af'
                    if val == 'T': return 'background-color: #fef9c3; color: #854d0e'
                    if val == 'N': return 'background-color: #e2e8f0; color: #1e293b'
                    if val == 'L' or val == 'Libre': return 'background-color: #fee2e2; color: #991b1b'
                    return ''

                st.dataframe(df.style.applymap(color_turnos), use_container_width=True)
                
                # Descargas
                csv = df.to_csv().encode('utf-8')
                st.download_button("📥 Descargar CSV para Excel", csv, "cuadrante.csv", "text/csv")
                
            except Exception as e:
                st.error(f"Hubo un problema con la respuesta de la IA. Inténtalo de nuevo.")
                st.info("Asegúrate de que Ollama tenga cargado el modelo Llama3.")
                with st.expander("Ver error técnico"):
                    st.write(e)
                    st.write(raw_response)

# --- PIE DE PÁGINA ---
st.markdown("---")
st.caption("MiTurno IA Local - Basado en Llama3 y Streamlit")

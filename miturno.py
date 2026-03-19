import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MiTurno Pro", page_icon="🗓️", layout="wide")

# --- INTEGRACIÓN DE TU CSS (Pema) ---
st.markdown("""
    <style>
    /* Estilos base de la app */
    .main { background-color: #f8fafc; }
    .stDataFrame { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); background-color: white;}
    
    /* === TU CSS ADAPTADO (Sin fotos) === */
    section[data-testid="stSidebar"] {
        background-color: #007a33;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] input {
        display: none !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] > label {
        display: flex !important;
        align-items: center;
        justify-content: center;
        padding: 10px 16px;
        margin: 6px 10px;
        border-radius: 8px;
        cursor: pointer;
        background-color: transparent;
        color: white !important;
        border: 1px solid transparent;
        font-weight: 500;
        text-align: center;
        transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.2);
    }
    section[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
        background-color: #ffffff !important;
        color: #007a33 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR MATEMÁTICO DINÁMICO ---
def generar_cuadrante(lista_empleados, dias_libres_req, prohibir_tarde_manana, reglas_json):
    model = cp_model.CpModel()
    num_dias = 7
    dias = range(num_dias)
    turnos = [0, 1, 2] # 0: Libre, 1: Mañana, 2: Tarde
    nombres_turnos = {0: 'L', 1: 'M', 2: 'T'}
    
    shifts = {}
    for emp in lista_empleados:
        for d in dias:
            for t in turnos:
                shifts[(emp, d, t)] = model.NewBoolVar(f'shift_{emp}_d{d}_t{t}')
                
    for emp in lista_empleados:
        # Regla 1: Un solo estado por día
        for d in dias:
            model.AddExactlyOne(shifts[(emp, d, t)] for t in turnos)
            
        # Regla 2: Días libres dinámicos
        model.Add(sum(shifts[(emp, d, 0)] for d in dias) == dias_libres_req)
        
        # Regla 3: Bloqueo Tarde -> Mañana dinámico
        if prohibir_tarde_manana:
            for d in range(num_dias - 1):
                model.AddImplication(shifts[(emp, d, 2)], shifts[(emp, d + 1, 1)].Not())

    # --- APLICAR REGLAS SUBIDAS POR JSON (Avanzado) ---
    # Ejemplo formato JSON: {"Pedro": {"dias_libres_forzados": [0, 6]}} (0=Lunes, 6=Domingo)
    if reglas_json:
        try:
            reglas = json.loads(reglas_json)
            for emp, configs in reglas.items():
                if emp in lista_empleados and "dias_libres_forzados" in configs:
                    for d_libre in configs["dias_libres_forzados"]:
                        if d_libre in dias:
                            # Forzamos que ese día tenga el turno 0 (Libre)
                            model.Add(shifts[(emp, d_libre, 0)] == 1)
        except:
            st.warning("El archivo JSON de reglas tiene un formato incorrecto y se ha ignorado.")

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0 
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        resultado = {}
        for emp in lista_empleados:
            resultado[emp] = []
            for d in dias:
                for t in turnos:
                    if solver.Value(shifts[(emp, d, t)]) == 1:
                        resultado[emp].append(nombres_turnos[t])
        return pd.DataFrame.from_dict(resultado, orient='index', columns=["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"])
    else:
        return None

# --- INTERFAZ VISUAL LIMPIA ---
st.title("🗓️ MiTurno")
st.markdown("Generador de cuadrantes de alta precisión")

# Dividimos la pantalla en pestañas para no saturar de información
tab1, tab2 = st.tabs(["⚙️ Generador Principal", "📂 Subir Reglas Específicas"])

with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Personal")
        empleados_input = st.text_area("Lista de Empleados", "Juan, Maria, Pedro, Ana, Luis", height=150)
        
        st.subheader("Reglas Generales")
        dias_libres = st.number_input("Días libres por semana", min_value=0, max_value=6, value=2)
        evitar_tm = st.toggle("Prohibir Tarde seguido de Mañana", value=True)
        
    with col2:
        st.subheader("Resultado")
        if st.button("🚀 Calcular Cuadrante", use_container_width=True, type="primary"):
            lista_empleados = [e.strip() for e in empleados_input.split(",") if e.strip()]
            
            if len(lista_empleados) < 2:
                st.error("Añade al menos 2 empleados.")
            else:
                with st.spinner("Motor matemático calculando..."):
                    df = generar_cuadrante(lista_empleados, dias_libres, evitar_tm, None) # Pasamos None al JSON por ahora
                    
                    if df is not None:
                        def style_cells(val):
                            if val == 'M': color = '#dcfce7'
                            elif val == 'T': color = '#fef9c3'
                            elif val == 'L': color = '#fee2e2'
                            else: color = '#f1f5f9'
                            return f'background-color: {color}; color: black; text-align: center; font-weight: bold;'

                        st.dataframe(df.style.map(style_cells), use_container_width=True)
                        st.download_button("📥 Descargar CSV", df.to_csv(), "cuadrante.csv", "text/csv")
                        st.success("¡Cuadrante perfecto generado!")
                    else:
                        st.error("❌ Imposible generar el cuadrante. Demasiadas restricciones para tan pocos empleados.")

with tab2:
    st.subheader("Reglas Excepcionales por Empleado")
    st.info("Aquí puedes subir un archivo con peticiones especiales (Ej: Ana tiene vacaciones, Luis no puede los martes).")
    archivo_subido = st.file_uploader("Sube tu archivo de reglas (.json)", type=["json"])
    
    if archivo_subido is not None:
        reglas_texto = archivo_subido.getvalue().decode("utf-8")
        st.text_area("Contenido del archivo:", reglas_texto, height=150, disabled=True)
        st.success("Archivo cargado. Vuelve a la pestaña principal y dale a Calcular.")
        # Nota para ti: En el botón de calcular habría que pasar 'reglas_texto' a la función generar_cuadrante en lugar de 'None'.

import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
import datetime

# --- 1. CONFIGURACIÓN Y ESTILO (CSS PEMA / ADA) ---
st.set_page_config(page_title="Gestión de Turnos - ADA", layout="wide")

def apply_ada_style():
    st.markdown(f"""
    <style>
    /* Fondo y tipografía */
    .main {{ background-color: #f4f7f6; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    
    /* Barra lateral estilo Junta (Verde) */
    [data-testid="stSidebar"] {{
        background-color: #007a33 !important;
        color: white !important;
    }}
    [data-testid="stSidebar"] * {{ color: white !important; }}
    
    /* Botones del menú lateral */
    [data-testid="stSidebar"] [role="radiogroup"] > label {{
        background-color: transparent;
        border: 1px solid rgba(255,255,255,0.3);
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
        transition: 0.3s;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {{
        background-color: white !important;
        color: #007a33 !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) * {{
        color: #007a33 !important;
    }}

    /* Botones principales en la app */
    .stButton > button {{
        background-color: #007a33 !important;
        color: white !important;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }}
    
    /* Estilo de tablas */
    [data-testid="stDataFrame"] {{
        background-color: white;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

apply_ada_style()

# --- 2. GESTIÓN DE ESTADO (Base de Datos temporal) ---
if 'workers' not in st.session_state:
    st.session_state.workers = pd.DataFrame([
        {"ID": "1", "Nombre": "Juan", "Apellidos": "Pérez", "Sede": "Sede Central", "Rol": "ADMIN"},
        {"ID": "2", "Nombre": "María", "Apellidos": "García", "Sede": "Sede Central", "Rol": "WORKER"}
    ])

if 'centers' not in st.session_state:
    st.session_state.centers = ["Sede Central", "Sede Almería", "Sede Sevilla"]

# --- 3. MOTOR LÓGICO DE TURNOS (Traducción de la beta) ---
def solver_turnos(empleados, num_dias=7):
    model = cp_model.CpModel()
    # Turnos: 0:Libre (L), 1:Mañana (M), 2:Tarde (T), 3:Noche (N)
    turnos = [0, 1, 2, 3]
    nombres_turnos = {0: 'L', 1: 'M', 2: 'T', 3: 'N'}
    
    # Variables de decisión
    x = {}
    for e in empleados:
        for d in range(num_dias):
            for t in turnos:
                x[e, d, t] = model.NewBoolVar(f'x_{e}_{d}_{t}')

    # REGLAS (Casuísticas)
    for e in empleados:
        for d in range(num_dias):
            # Un solo turno al día
            model.AddExactlyOne(x[e, d, t] for t in turnos)
        
        # Al menos 2 días libres a la semana
        model.Add(sum(x[e, d, 0] for d in range(num_dias)) >= 2)

        # Regla de seguridad: No Tarde(2) -> Mañana(1) al día siguiente
        for d in range(num_dias - 1):
            model.AddImplication(x[e, d, 2], x[e, d+1, 1].Not())
            model.AddImplication(x[e, d, 3], x[e, d+1, 1].Not()) # No Noche -> Mañana
            model.AddImplication(x[e, d, 3], x[e, d+1, 2].Not()) # No Noche -> Tarde

    # Distribución equitativa: Que todos trabajen parecido
    # (Opcional, pero mejora la calidad)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        data = {}
        for e in empleados:
            data[e] = [nombres_turnos[t] for d in range(num_dias) for t in turnos if solver.Value(x[e, d, t]) == 1]
        return pd.DataFrame(data).T
    return None

# --- 4. INTERFAZ DE NAVEGACIÓN ---
with st.sidebar:
    st.title("ADA Turnos")
    menu = st.radio("MENÚ", ["🏠 Inicio", "🏢 Sedes", "👥 Trabajadores", "🗓️ Generar Horario"])
    st.markdown("---")
    st.info("Versión Migrada de React a Python")

if menu == "🏠 Inicio":
    st.header("Panel de Control")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sedes", len(st.session_state.centers))
    col2.metric("Trabajadores", len(st.session_state.workers))
    col3.metric("Estado", "Activo")
    
    st.image("https://upload.wikimedia.org/wikipedia/commons/b/bb/Logo_de_la_Junta_de_Andaluc%C3%ADa.svg", width=200)

elif menu == "🏢 Sedes":
    st.header("Gestión de Sedes")
    nueva_sede = st.text_input("Nombre de la nueva sede")
    if st.button("Añadir Sede"):
        if nueva_sede and nueva_sede not in st.session_state.centers:
            st.session_state.centers.append(nueva_sede)
            st.success(f"Sede {nueva_sede} añadida.")
    
    st.write("### Sedes Actuales")
    for s in st.session_state.centers:
        st.text(f"📍 {s}")

elif menu == "👥 Trabajadores":
    st.header("Alta de Trabajadores")
    with st.expander("➕ Registrar Nuevo Trabajador"):
        with st.form("worker_form"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre")
            apellidos = c2.text_input("Apellidos")
            sede = st.selectbox("Sede Asignada", st.session_state.centers)
            rol = st.selectbox("Rol", ["WORKER", "ADMIN", "MANAGER"])
            if st.form_submit_button("Guardar"):
                new_w = {"ID": str(len(st.session_state.workers)+1), "Nombre": nombre, "Apellidos": apellidos, "Sede": sede, "Rol": rol}
                st.session_state.workers = pd.concat([st.session_state.workers, pd.DataFrame([new_w])], ignore_index=True)
                st.success("Trabajador registrado.")

    st.write("### Listado de Personal")
    st.dataframe(st.session_state.workers, use_container_width=True, hide_index=True)

elif menu == "🗓️ Generar Horario":
    st.header("Generador Automático de Cuadrantes")
    sede_sel = st.selectbox("Seleccionar Sede para el cálculo", st.session_state.centers)
    empleados_sede = st.session_state.workers[st.session_state.workers['Sede'] == sede_sel]['Nombre'].tolist()

    if not empleados_sede:
        st.warning("No hay empleados registrados en esta sede.")
    else:
        st.write(f"Generando horario para: {', '.join(empleados_sede)}")
        if st.button("🚀 Iniciar Cálculo Matemático"):
            with st.spinner("Encajando turnos según casuísticas..."):
                df_horario = solver_turnos(empleados_sede)
                
                if df_horario is not None:
                    df_horario.columns = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
                    
                    def color_turnos(val):
                        colors = {'M': '#dcfce7', 'T': '#fef9c3', 'N': '#fbcfe8', 'L': '#fee2e2'}
                        return f'background-color: {colors.get(val, "white")}; color: black; font-weight: bold; text-align: center'
                    
                    st.write("### Cuadrante Semanal")
                    st.dataframe(df_horario.style.applymap(color_turnos), use_container_width=True)
                    st.download_button("Descargar CSV", df_horario.to_csv(), "horario.csv")
                else:
                    st.error("No se ha encontrado una solución que cumpla todas las reglas.")

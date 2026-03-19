import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import calendar
from ortools.sat.python import cp_model

# --- 1. CONFIGURACIÓN Y ESTILOS (ADA/PEMA) ---
st.set_page_config(page_title="MiTurno - Gestión de Centros ADA", layout="wide", page_icon="🗓️")

def cargar_estilos_corporativos():
    # Inyectamos tu CSS pema(1).css adaptado para Streamlit
    st.markdown("""
        <style>
        /* Fondo base */
        .main { background-color: #f8fafc; }
        
        /* Barra lateral Verde Junta */
        [data-testid="stSidebar"] {
            background-color: #007a33 !important;
            color: white !important;
        }
        [data-testid="stSidebar"] * { color: white !important; }
        
        /* Estilo de los botones del menú (extraído de tu CSS) */
        [data-testid="stSidebar"] [role="radiogroup"] > label {
            display: flex !important;
            align-items: center;
            padding: 12px 20px;
            margin: 8px 12px;
            border-radius: 10px;
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label:hover {
            background-color: rgba(255, 255, 255, 0.2);
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
            background-color: #ffffff !important;
            color: #007a33 !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) * {
            color: #007a33 !important;
        }

        /* Títulos y Cards */
        h1, h2, h3 { color: #007a33 !important; font-weight: 800; }
        .glass-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 20px;
        }
        
        /* Botones Principales */
        .stButton > button {
            background: #007a33 !important;
            color: white !important;
            border-radius: 8px;
            font-weight: 600;
            border: none;
            padding: 10px 24px;
        }
        </style>
    """, unsafe_allow_html=True)

cargar_estilos_corporativos()

# --- 2. BASE DE DATOS (ESTADO) ---
# Inicializamos los centros tal cual estaban en el código React [cite: 35]
if 'db' not in st.session_state:
    st.session_state.db = {
        'centers': [
            {'id': '1', 'name': 'Museo de Úbeda'},
            {'id': '2', 'name': 'Museo Provincial de Jaén'},
            {'id': '3', 'name': 'Museo Ibero'},
            {'id': '4', 'name': 'Museo de Cazorla'},
            {'id': '5', 'name': 'Conjunto Arqueológico Cástulo'}
        ],
        'workers': [
            {'id': 'w1', 'name': 'Juan', 'surname': 'Pérez', 'center_id': '1', 'role': 'EDITOR'},
            {'id': 'w2', 'name': 'María', 'surname': 'García', 'center_id': '1', 'role': 'READER'},
            {'id': 'w3', 'name': 'Luis', 'surname': 'Rodríguez', 'center_id': '2', 'role': 'WORKER'}
        ],
        'shifts': [] # Formato: {'worker_id': 'w1', 'date': '2024-03-20', 'type': 'M'}
    }

# --- 3. LÓGICA DE TURNOS (TRADUCCIÓN DE LA BETA) ---
# Definimos los tipos de turnos igual que en React [cite: 36, 55]
SHIFT_TYPES = {
    'M': {'name': 'Mañana', 'color': '#fbbf24', 'hours': 7},
    'T': {'name': 'Tarde', 'color': '#f97316', 'hours': 7},
    'N': {'name': 'Noche', 'color': '#1e3a8a', 'hours': 10},
    'Mr': {'name': 'Mañana Reducida', 'color': '#fcd34d', 'hours': 5},
    'Tr': {'name': 'Tarde Reducida', 'color': '#fb923c', 'hours': 5},
    'L': {'name': 'Libre', 'color': '#fee2e2', 'hours': 0},
    'V': {'name': 'Vacaciones', 'color': '#10b981', 'hours': 0},
    'B': {'name': 'Baja', 'color': '#ef4444', 'hours': 0}
}

def solver_automatico(workers_ids, start_date):
    model = cp_model.CpModel()
    num_days = 7
    # 0=L, 1=M, 2=T, 3=N (Simplificado para el ejemplo)
    shifts = [0, 1, 2, 3]
    map_ids = {0: 'L', 1: 'M', 2: 'T', 3: 'N'}
    
    x = {}
    for w in workers_ids:
        for d in range(num_days):
            for s in shifts:
                x[w, d, s] = model.NewBoolVar(f'x_{w}_{d}_{s}')

    for w in workers_ids:
        for d in range(num_days):
            model.AddExactlyOne(x[w, d, s] for s in shifts)
        # Regla: No Tarde(2) o Noche(3) antes de Mañana(1) 
        for d in range(num_days - 1):
            model.AddImplication(x[w, d, 2], x[w, d+1, 1].Not())
            model.AddImplication(x[w, d, 3], x[w, d+1, 1].Not())
        # Mínimo 2 días libres 
        model.Add(sum(x[w, d, 0] for d in range(num_days)) >= 2)

    solver = cp_model.CpSolver()
    if solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        new_shifts = []
        for d in range(num_days):
            curr_date = (start_date + timedelta(days=d)).strftime('%Y-%m-%d')
            for w in workers_ids:
                for s in shifts:
                    if solver.Value(x[w, d, s]):
                        new_shifts.append({'worker_id': w, 'date': curr_date, 'type': map_ids[s]})
        return new_shifts
    return None

# --- 4. INTERFAZ DE NAVEGACIÓN ---
with st.sidebar:
    st.image("https://www.ada.es/export/sites/ada/.content/imagenes/logo-ada.png", width=180)
    st.markdown("### PANEL DE CONTROL")
    menu = st.radio("Menú", ["🏠 Inicio", "🏢 Sedes", "👥 Trabajadores", "🗓️ Cuadrante Mensual", "🤖 Generador IA"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("© 2024 Agencia Digital de Andalucía")

if menu == "🏠 Inicio":
    st.title("Bienvenido a MiTurno ADA")
    st.markdown("Gestión centralizada de horarios para los museos y centros de Andalucía.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="glass-card"><h3>{len(st.session_state.db["centers"])}</h3><p>Sedes Activas</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="glass-card"><h3>{len(st.session_state.db["workers"])}</h3><p>Personal</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="glass-card"><h3>{len(st.session_state.db["shifts"])}</h3><p>Turnos Asignados</p></div>', unsafe_allow_html=True)

elif menu == "🏢 Sedes":
    st.title("Gestión de Sedes")
    with st.expander("➕ Añadir Nueva Sede"):
        name = st.text_input("Nombre del Centro/Museo")
        if st.button("Guardar Sede"):
            new_id = str(len(st.session_state.db['centers']) + 1)
            st.session_state.db['centers'].append({'id': new_id, 'name': name})
            st.success("Sede añadida correctamente.")
    
    st.write("### Listado de Centros")
    df_centers = pd.DataFrame(st.session_state.db['centers'])
    st.table(df_centers)

elif menu == "👥 Trabajadores":
    st.title("Personal de Centros")
    with st.form("new_worker"):
        col1, col2 = st.columns(2)
        name = col1.text_input("Nombre")
        surname = col2.text_input("Apellidos")
        center = st.selectbox("Sede Asignada", [c['name'] for c in st.session_state.db['centers']])
        role = st.selectbox("Rol", ["WORKER", "EDITOR", "ADMIN"])
        if st.form_submit_button("Registrar Trabajador"):
            c_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == center)
            new_w = {'id': f'w{len(st.session_state.db["workers"])+1}', 'name': name, 'surname': surname, 'center_id': c_id, 'role': role}
            st.session_state.db['workers'].append(new_w)
            st.success("Trabajador registrado.")
            
    st.write("### Plantilla")
    st.dataframe(pd.DataFrame(st.session_state.db['workers']), use_container_width=True)

elif menu == "🗓️ Cuadrante Mensual":
    st.title("Cuadrante de Turnos")
    center_sel = st.selectbox("Filtrar por Sede", [c['name'] for c in st.session_state.db['centers']])
    c_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == center_sel)
    
    # Filtrar trabajadores y sus turnos
    workers_sede = [w for w in st.session_state.db['workers'] if w['center_id'] == c_id]
    
    if not workers_sede:
        st.warning("No hay trabajadores en esta sede.")
    else:
        # Replicamos la tabla del RosterView de React 
        hoy = datetime.now()
        mes = hoy.month
        anio = hoy.year
        num_dias = calendar.monthrange(anio, mes)[1]
        
        data_roster = {}
        for w in workers_sede:
            nombre_full = f"{w['name']} {w['surname']}"
            data_roster[nombre_full] = [""] * num_dias
            for s in st.session_state.db['shifts']:
                if s['worker_id'] == w['id']:
                    d_idx = int(s['date'].split("-")[2]) - 1
                    if d_idx < num_dias:
                        data_roster[nombre_full][d_idx] = s['type']
        
        df_roster = pd.DataFrame(data_roster).T
        df_roster.columns = [str(i+1) for i in range(num_dias)]
        
        def color_roster(val):
            color = SHIFT_TYPES.get(val, {}).get('color', 'white')
            text_color = 'white' if val in ['N', 'T', 'B', 'V'] else 'black'
            return f'background-color: {color}; color: {text_color}; text-align: center; font-weight: bold'

        st.dataframe(df_roster.style.applymap(color_roster), use_container_width=True)

elif menu == "🤖 Generador IA":
    st.title("Generador Automático de Horarios")
    st.info("Esta sección utiliza el motor lógico para rellenar los turnos vacíos cumpliendo todas las normativas.")
    
    sede_gen = st.selectbox("Seleccionar Sede para Generar", [c['name'] for c in st.session_state.db['centers']])
    fecha_inicio = st.date_input("Fecha de inicio (Lunes)", value=datetime.now())
    
    if st.button("🚀 Iniciar Generación de Turnos"):
        c_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == sede_gen)
        w_ids = [w['id'] for w in st.session_state.db['workers'] if w['center_id'] == c_id]
        
        with st.spinner("Calculando cuadrante óptimo..."):
            nuevos_turnos = solver_automatico(w_ids, fecha_inicio)
            if nuevos_turnos:
                st.session_state.db['shifts'].extend(nuevos_turnos)
                st.success(f"¡Generados {len(nuevos_turnos)} turnos con éxito!")
            else:
                st.error("No se pudo encontrar una solución válida con el personal actual.")

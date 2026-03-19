import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="MiTurno Optimizado", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stDataFrame { background-color: white; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🗓️ MiTurno: Motor de Alta Velocidad (Puerto 8505)")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración")
    st.success("⚡ Motor Matemático Activado (OR-Tools)")
    empleados_input = st.text_area("Lista de Empleados (separados por coma)", "Juan, Maria, Pedro, Ana, Luis")
    
    st.info("""
    **Reglas estrictas aplicadas:**
    1. Cada empleado libra exactamente 2 días.
    2. Solo 1 turno por día (M, T o L).
    3. Prohibido trabajar Tarde y luego Mañana.
    """)

# --- LÓGICA DEL MOTOR MATEMÁTICO (Alta velocidad) ---
def generar_cuadrante_rapido(lista_empleados):
    model = cp_model.CpModel()
    num_dias = 7
    dias = range(num_dias)
    
    # 0: Libre (L), 1: Mañana (M), 2: Tarde (T)
    turnos = [0, 1, 2] 
    nombres_turnos = {0: 'L', 1: 'M', 2: 'T'}
    
    # Variables
    shifts = {}
    for emp in lista_empleados:
        for d in dias:
            for t in turnos:
                shifts[(emp, d, t)] = model.NewBoolVar(f'shift_{emp}_d{d}_t{t}')
                
    # Restricciones
    for emp in lista_empleados:
        for d in dias:
            # Regla: Exactamente un turno asignado por día
            model.AddExactlyOne(shifts[(emp, d, t)] for t in turnos)
            
        # Regla: Exactamente 2 días libres por semana
        model.Add(sum(shifts[(emp, d, 0)] for d in dias) == 2)
        
        # Regla: Si hoy es Tarde, mañana no puede ser Mañana
        for d in range(num_dias - 1):
            model.AddImplication(shifts[(emp, d, 2)], shifts[(emp, d + 1, 1)].Not())

    # Solver
    solver = cp_model.CpSolver()
    # Optimización: Límite de tiempo por si en el futuro pones reglas imposibles
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

# --- INTERFAZ PRINCIPAL ---
if st.button("🚀 Generar Cuadrante al Instante"):
    lista_empleados = [e.strip() for e in empleados_input.split(",") if e.strip()]
    
    if not lista_empleados:
        st.error("Por favor, introduce al menos un empleado.")
    else:
        with st.spinner("Calculando combinaciones a la velocidad de la luz..."):
            df = generar_cuadrante_rapido(lista_empleados)
            
            if df is not None:
                # Damos color a las celdas para que se lea mejor
                def style_cells(val):
                    if val == 'M': color = '#dcfce7' # Verde claro
                    elif val == 'T': color = '#fef9c3' # Amarillo claro
                    elif val == 'L': color = '#fee2e2' # Rojo claro
                    else: color = '#f1f5f9'
                    return f'background-color: {color}; color: black; text-align: center;'

                st.dataframe(df.style.map(style_cells), use_container_width=True)
                
                # Botón de descarga CSV
                csv = df.to_csv()
                st.download_button("📥 Descargar CSV", csv, "cuadrante_optimizado.csv", "text/csv")
                st.success(f"¡Cuadrante perfecto generado para {len(lista_empleados)} empleados!")
            else:
                st.error("❌ Conflicto de reglas: Es matemáticamente imposible generar un cuadrante con esas condiciones.")

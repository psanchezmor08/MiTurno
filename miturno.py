import streamlit as st
from PIL import Image
import pandas as pd

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
# Es vital que esto sea lo primero. Define el título de la pestaña y el layout ancho.
st.set_page_config(
    page_title="Aplicación Corporativa - Junta de Andalucía",
    page_icon="🟢", # Puedes poner aquí un icono .ico o un emoji
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INYECCIÓN DE CSS CORPORATIVO (Estilo Junta) ---
# Esta función "engaña" a Streamlit para que use tus estilos en lugar de los suyos.
# He adaptado los estilos verdes y la tipografía Roboto para que funcionen aquí.
def cargar_estilos_junta():
    estilo_css = """
    <style>
        /* Importamos la fuente Roboto oficial de Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

        :root {
            --verde-junta: #007a33;        /* Color principal */
            --verde-junta-claro: #e6f2eb;  /* Fondos claros */
            --verde-junta-oscuro: #005f27; /* Hover de botones */
            --texto-gris: #333333;
        }

        /* Aplicar tipografía global */
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
            color: var(--texto-gris);
        }

        /* --- PERSONALIZACIÓN DE TÍTULOS --- */
        h1, h2, h3 {
            color: var(--verde-junta) !important;
            font-weight: 700;
        }

        /* --- PERSONALIZACIÓN DE LA BARRA LATERAL (Sidebar) --- */
        [data-testid="stSidebar"] {
            background-color: var(--verde-junta-claro);
            border-right: 1px solid #d1e7dd;
        }
        /* Estilo para los radio buttons del menú lateral */
        [data-testid="stSidebar"] [role="radiogroup"] label {
            background-color: white;
            border: 1px solid #d1e7dd;
            margin-bottom: 5px;
            border-radius: 4px;
            padding: 10px;
            transition: all 0.3s;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {
            background-color: var(--verde-junta) !important;
            color: white !important;
            font-weight: 500;
            border-color: var(--verde-junta);
        }

        /* --- PERSONALIZACIÓN DE BOTONES PRINCIPALES --- */
        /* Apuntamos a los botones de Streamlit para hacerlos verdes */
        .stButton > button {
            background-color: var(--verde-junta) !important;
            color: white !important;
            border: none;
            border-radius: 4px;
            padding: 0.6rem 1.2rem;
            font-weight: 500;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: background-color 0.3s ease;
        }
        .stButton > button:hover {
            background-color: var(--verde-junta-oscuro) !important;
             box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        /* Botones secundarios (tipo 'outline' si los necesitaras) */
        button[kind="secondary"] {
             background-color: transparent !important;
             color: var(--verde-junta) !important;
             border: 2px solid var(--verde-junta) !important;
        }

        /* --- PERSONALIZACIÓN DE INPUTS (Campos de texto) --- */
        /* Cuando haces clic en un input, el borde se pone verde */
        [data-baseweb="input"]:focus-within {
            border-color: var(--verde-junta) !important;
            box-shadow: 0 0 0 1px var(--verde-junta) !important;
        }

        /* --- ESTILO DE TABLAS/DATAFRAMES --- */
        [data-testid="stDataFrame"] {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }
        /* Cabecera de la tabla en verde claro */
        [data-testid="stDataFrame"] thead th {
            background-color: var(--verde-junta-claro) !important;
            color: var(--verde-junta) !important;
            font-weight: 700 !important;
        }

        /* Eliminar el menú hamburguesa y el footer de "Made with Streamlit" para que sea más limpio */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """
    st.markdown(estilo_css, unsafe_allow_html=True)

# Ejecutamos la función para cargar el CSS
cargar_estilos_junta()


# --- 3. ESTRUCTURA DE LA APLICACIÓN (Ejemplo) ---

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    # Aquí podrías poner el logo de la Junta
    # st.image("ruta_al_logo_junta.png", width=200)
    st.header("Navegación Principal")
    menu_seleccionado = st.radio("Ir a:", ["Inicio / Dashboard", "Gestión de Datos", "Configuración"], label_visibility="collapsed")

    st.markdown("---")
    st.caption("© 2024 Junta de Andalucía. v1.0.0 (Python Edition)")

# --- Área Principal ---
if menu_seleccionado == "Inicio / Dashboard":
    st.title("Bienvenido al Sistema")
    st.markdown("Esta aplicación ha sido portada a **Python + Streamlit** manteniendo la identidad visual corporativa.")

    # Creamos dos columnas para organizar el contenido
    col_izq, col_der = st.columns([1, 2])

    with col_izq:
        st.subheader("Controles Rápidos")
        # Ejemplo de inputs con el estilo aplicado
        usuario = st.text_input("Identificador de usuario")
        departamento = st.selectbox("Seleccione departamento", ["Consejería de Salud", "Educación", "Fomento"])
        
        st.write("") # Espacio
        if st.button("Validar Acceso", use_container_width=True):
            if usuario:
                st.success(f"Acceso validado para: **{usuario}** ({departamento})")
            else:
                st.warning("Por favor, introduzca un usuario.")

    with col_der:
        st.subheader("Vista General de Datos")
        # Creamos un contenedor con estilo de tarjeta
        with st.container():
            st.info("Aquí se mostrará la información principal importada de la lógica de React.")
            
            # Ejemplo de tabla con datos ficticios para ver el estilo
            datos_ejemplo = pd.DataFrame({
                'ID Expediente': ['EXP-001', 'EXP-002', 'EXP-003', 'EXP-004'],
                'Estado': ['En Trámite', 'Resuelto', 'Pendiente', 'En Trámite'],
                'Fecha Entrada': ['2023-10-01', '2023-10-05', '2023-10-10', '2023-10-12'],
                'Prioridad': ['Alta', 'Baja', 'Media', 'Alta']
            })
            st.dataframe(datos_ejemplo, use_container_width=True, hide_index=True)

elif menu_seleccionado == "Gestión de Datos":
    st.title("Gestión de Expedientes")
    st.write("Pantalla secundaria para la operativa diaria.")
    # Aquí iría la lógica de negocio compleja

elif menu_seleccionado == "Configuración":
    st.title("Ajustes del Sistema")
    st.write("Parámetros de configuración de la aplicación.")

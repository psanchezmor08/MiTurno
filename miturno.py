import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import calendar
import os
from collections import defaultdict
from ortools.sat.python import cp_model
import mysql.connector

CENTER_UBEDA = '1'
CENTER_JAEN = '2'

EXAMPLE_WORKERS = [
    {'id': 'w1', 'name': 'Pilar', 'surname': 'Barragán', 'center_id': CENTER_UBEDA, 'role': 'WORKER'},
    {'id': 'w2', 'name': 'Tomás', 'surname': 'Pino', 'center_id': CENTER_UBEDA, 'role': 'WORKER'},
    {'id': 'w3', 'name': 'Juana', 'surname': 'García', 'center_id': CENTER_UBEDA, 'role': 'WORKER'},
    {'id': 'w4', 'name': 'Francisco', 'surname': 'Pérez', 'center_id': CENTER_UBEDA, 'role': 'WORKER'},
    {'id': 'w5', 'name': 'Mercedes', 'surname': 'Rodríguez', 'center_id': CENTER_UBEDA, 'role': 'WORKER'},
    {'id': 'w6', 'name': 'Ana', 'surname': 'Garrido', 'center_id': CENTER_JAEN, 'role': 'WORKER'},
    {'id': 'w7', 'name': 'Juan Antonio', 'surname': 'Simarro', 'center_id': CENTER_JAEN, 'role': 'WORKER'},
    {'id': 'w8', 'name': 'Francisco Ginés', 'surname': 'Cruz', 'center_id': CENTER_JAEN, 'role': 'WORKER'},
    {'id': 'w9', 'name': 'Joaquín', 'surname': 'Casas', 'center_id': CENTER_JAEN, 'role': 'WORKER'}
]

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
        'workers': EXAMPLE_WORKERS.copy(),
        'shifts': [], # Formato: {'worker_id': 'w1', 'date': '2024-03-20', 'type': 'M'}
        'requirements_global': [
            {'key': 'monday_closed', 'description': 'Cierre de sedes los lunes', 'enabled': True, 'value': '1'},
            {'key': 'summer_only_morning', 'description': 'En verano solo turno de mañana (15/06 al 15/09)', 'enabled': True, 'value': '1'},
            {'key': 'min_workers_per_shift', 'description': 'Mínimo de trabajadores por turno', 'enabled': True, 'value': '2'},
            {'key': 'weekly_rest_days', 'description': 'Descansos semanales mínimos por trabajador', 'enabled': True, 'value': '2'},
            {'key': 'minimum_rest_hours', 'description': 'Descanso mínimo entre jornadas (horas)', 'enabled': True, 'value': '18'},
            {'key': 'rotation_required', 'description': 'Debe existir rotación entre mañana/tarde/noche', 'enabled': True, 'value': '1'},
            {'key': 'max_work_days_year', 'description': 'Límite anual de días trabajados', 'enabled': True, 'value': '246'},
            {'key': 'compensation_after_sunday_holiday', 'description': 'Compensación tras domingo/festivo', 'enabled': True, 'value': '1'},
            {'key': 'mandatory_closed_holidays', 'description': 'Festivos con cierre obligatorio (01/01,06/01,01/05,24/12,25/12,31/12)', 'enabled': True, 'value': '1'}
        ],
        'requirements_weekly': [],
        'verification_history': []
    }

if 'last_verification_by_center' not in st.session_state:
    st.session_state.last_verification_by_center = {}

if 'mysql_connected' not in st.session_state:
    st.session_state.mysql_connected = False

if 'mysql_last_error' not in st.session_state:
    st.session_state.mysql_last_error = ''


def mysql_is_configured():
    return bool(os.getenv('MYSQL_HOST'))


def get_mysql_connection(use_database=True):
    conn_kwargs = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', '')
    }
    if use_database:
        conn_kwargs['database'] = os.getenv('MYSQL_DATABASE', 'miturno')
    return mysql.connector.connect(**conn_kwargs)


def init_mysql_schema():
    if not mysql_is_configured():
        st.session_state.mysql_last_error = 'MYSQL_HOST no está configurado en el entorno.'
        return False

    db_name = os.getenv('MYSQL_DATABASE', 'miturno')
    conn = None
    cursor = None
    try:
        conn = get_mysql_connection(use_database=False)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.close()
        conn.close()

        conn = get_mysql_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS workers (
                id VARCHAR(40) PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                surname VARCHAR(120) NOT NULL,
                center_id VARCHAR(20) NOT NULL,
                role VARCHAR(30) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        st.session_state.mysql_connected = True
        st.session_state.mysql_last_error = ''
        return True
    except mysql.connector.Error as e:
        st.session_state.mysql_connected = False
        st.session_state.mysql_last_error = str(e)
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def seed_workers_if_empty(workers_seed):
    if not st.session_state.mysql_connected:
        return

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM workers")
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.executemany(
                "INSERT INTO workers (id, name, surname, center_id, role) VALUES (%s, %s, %s, %s, %s)",
                [(w['id'], w['name'], w['surname'], w['center_id'], w['role']) for w in workers_seed]
            )
            conn.commit()
    except mysql.connector.Error as e:
        st.session_state.mysql_connected = False
        st.session_state.mysql_last_error = str(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def upsert_workers_mysql(workers_seed):
    if not st.session_state.mysql_connected:
        return

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection(use_database=True)
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO workers (id, name, surname, center_id, role)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                surname = VALUES(surname),
                center_id = VALUES(center_id),
                role = VALUES(role)
            """,
            [(w['id'], w['name'], w['surname'], w['center_id'], w['role']) for w in workers_seed]
        )
        conn.commit()
    except mysql.connector.Error as e:
        st.session_state.mysql_connected = False
        st.session_state.mysql_last_error = str(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def load_workers_from_mysql():
    if not st.session_state.mysql_connected:
        return None

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection(use_database=True)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, surname, center_id, role FROM workers ORDER BY id")
        rows = cursor.fetchall()
        return [
            {
                'id': r['id'],
                'name': r['name'],
                'surname': r['surname'],
                'center_id': r['center_id'],
                'role': r['role']
            }
            for r in rows
        ]
    except mysql.connector.Error as e:
        st.session_state.mysql_connected = False
        st.session_state.mysql_last_error = str(e)
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def insert_worker_mysql(worker):
    if not st.session_state.mysql_connected:
        return False

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO workers (id, name, surname, center_id, role) VALUES (%s, %s, %s, %s, %s)",
            (worker['id'], worker['name'], worker['surname'], worker['center_id'], worker['role'])
        )
        conn.commit()
        return True
    except mysql.connector.Error as e:
        st.session_state.mysql_connected = False
        st.session_state.mysql_last_error = str(e)
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_worker_mysql(worker):
    if not st.session_state.mysql_connected:
        return False

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE workers SET name=%s, surname=%s, center_id=%s, role=%s WHERE id=%s",
            (worker['name'], worker['surname'], worker['center_id'], worker['role'], worker['id'])
        )
        conn.commit()
        return True
    except mysql.connector.Error as e:
        st.session_state.mysql_connected = False
        st.session_state.mysql_last_error = str(e)
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def delete_worker_mysql(worker_id):
    if not st.session_state.mysql_connected:
        return False

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM workers WHERE id=%s", (worker_id,))
        conn.commit()
        return True
    except mysql.connector.Error as e:
        st.session_state.mysql_connected = False
        st.session_state.mysql_last_error = str(e)
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def next_worker_id(workers):
    max_n = 0
    for w in workers:
        wid = str(w.get('id', ''))
        if wid.startswith('w') and wid[1:].isdigit():
            max_n = max(max_n, int(wid[1:]))
    return f'w{max_n + 1}'


def ensure_mysql_ready():
    # Reintenta conexión en cada recarga para evitar el falso "no disponible"
    # cuando MySQL tarda un poco en iniciar.
    if init_mysql_schema():
        seed_workers_if_empty(EXAMPLE_WORKERS)
        upsert_workers_mysql(EXAMPLE_WORKERS)
        workers_db = load_workers_from_mysql()
        if workers_db is not None:
            st.session_state.db['workers'] = workers_db


ensure_mysql_ready()


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ['1', 'true', 'yes', 'si', 'sí']


def parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_requirements_config():
    req_map = {r['key']: r for r in st.session_state.db.get('requirements_global', [])}
    # Reglas de cumplimiento estricto: siempre activas.
    cfg = {
        'monday_closed': True,
        'summer_only_morning': True,
        'min_workers_per_shift': parse_int(req_map.get('min_workers_per_shift', {}).get('value', 2), 2),
        'weekly_rest_days': parse_int(req_map.get('weekly_rest_days', {}).get('value', 2), 2),
        'minimum_rest_hours': parse_int(req_map.get('minimum_rest_hours', {}).get('value', 18), 18),
        'rotation_required': True,
        'max_work_days_year': parse_int(req_map.get('max_work_days_year', {}).get('value', 246), 246),
        'compensation_after_sunday_holiday': True,
        'mandatory_closed_holidays': True
    }
    return cfg


def is_summer_date(d):
    year = d.year
    start = datetime(year, 6, 15).date()
    end = datetime(year, 9, 15).date()
    return start <= d <= end


def fixed_holidays_for_year(year):
    return {
        datetime(year, 1, 1).date(),
        datetime(year, 1, 6).date(),
        datetime(year, 5, 1).date(),
        datetime(year, 12, 24).date(),
        datetime(year, 12, 25).date(),
        datetime(year, 12, 31).date()
    }


def shift_interval(day, shift_type):
    if shift_type == 'M':
        return datetime(day.year, day.month, day.day, 7, 0), datetime(day.year, day.month, day.day, 14, 0)
    if shift_type == 'T':
        return datetime(day.year, day.month, day.day, 14, 0), datetime(day.year, day.month, day.day, 21, 0)
    if shift_type == 'N':
        return datetime(day.year, day.month, day.day, 21, 0), datetime(day.year, day.month, day.day, 23, 59)
    return None, None


def build_weekly_min_workers_map(center_id):
    weekly_map = {}
    for row in st.session_state.db.get('requirements_weekly', []):
        if row.get('center_id') == center_id and row.get('enabled', True):
            weekly_map[row.get('week_key')] = parse_int(row.get('min_workers_per_shift', 2), 2)
    return weekly_map


def get_week_start(selected_date):
    return selected_date - timedelta(days=selected_date.weekday())


def get_week_label(week_start):
    iso = week_start.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def load_example_week_shifts(center_id, week_start):
    # Patrón de ejemplo basado en el PDF compartido para visualizar horarios reales por trabajador.
    ubeda_pattern = {
        1: {'M': ['Pilar Barragán', 'Tomás Pino'], 'T': ['Juana García', 'Francisco Pérez']},
        2: {'M': ['Mercedes Rodríguez', 'Francisco Pérez'], 'T': ['Pilar Barragán', 'Juana García']},
        3: {'M': ['Tomás Pino', 'Juana García'], 'T': ['Mercedes Rodríguez', 'Pilar Barragán']},
        4: {'M': ['Francisco Pérez', 'Pilar Barragán'], 'T': ['Tomás Pino', 'Mercedes Rodríguez']},
        5: {'M': ['Juana García', 'Mercedes Rodríguez'], 'T': ['Francisco Pérez', 'Tomás Pino']},
        6: {'M': ['Pilar Barragán', 'Francisco Pérez'], 'T': ['Juana García', 'Tomás Pino']}
    }

    jaen_pattern = {
        1: {'M': ['Ana Garrido', 'Juan Antonio Simarro'], 'T': ['Francisco Ginés Cruz', 'Joaquín Casas']},
        2: {'M': ['Francisco Ginés Cruz', 'Ana Garrido'], 'T': ['Juan Antonio Simarro', 'Joaquín Casas']},
        3: {'M': ['Joaquín Casas', 'Juan Antonio Simarro'], 'T': ['Ana Garrido', 'Francisco Ginés Cruz']},
        4: {'M': ['Ana Garrido', 'Joaquín Casas'], 'T': ['Francisco Ginés Cruz', 'Juan Antonio Simarro']},
        5: {'M': ['Juan Antonio Simarro', 'Francisco Ginés Cruz'], 'T': ['Ana Garrido', 'Joaquín Casas']},
        6: {'M': ['Joaquín Casas', 'Ana Garrido'], 'T': ['Juan Antonio Simarro', 'Francisco Ginés Cruz']}
    }

    pattern = ubeda_pattern if center_id == CENTER_UBEDA else jaen_pattern if center_id == CENTER_JAEN else {}
    if not pattern:
        return 0

    workers_center = [w for w in st.session_state.db['workers'] if w['center_id'] == center_id]
    workers_by_name = {f"{w['name']} {w['surname']}": w['id'] for w in workers_center}

    new_shifts = []
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        if day.weekday() == 0:
            continue  # lunes cerrado

        day_pattern = pattern.get(day.weekday())
        if not day_pattern:
            continue

        day_str = day.strftime('%Y-%m-%d')
        for shift_type in ['M', 'T']:
            for worker_name in day_pattern.get(shift_type, []):
                worker_id = workers_by_name.get(worker_name)
                if worker_id:
                    new_shifts.append({'worker_id': worker_id, 'date': day_str, 'type': shift_type})

    center_worker_ids = {w['id'] for w in workers_center}
    new_dates = {s['date'] for s in new_shifts}
    st.session_state.db['shifts'] = [
        s for s in st.session_state.db['shifts']
        if not (s['worker_id'] in center_worker_ids and s['date'] in new_dates)
    ]

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for s in new_shifts:
        s['source'] = 'PDF_EJEMPLO'
        s['created_at'] = timestamp
    st.session_state.db['shifts'].extend(new_shifts)
    return len(new_shifts)


def verify_center_requirements(center_id, week_start=None):
    workers = [w for w in st.session_state.db['workers'] if w['center_id'] == center_id]
    workers_map = {w['id']: w for w in workers}
    center_shifts = [s for s in st.session_state.db['shifts'] if s['worker_id'] in workers_map]

    if week_start is not None:
        week_end = week_start + timedelta(days=6)
        center_shifts = [
            s for s in center_shifts
            if week_start <= datetime.strptime(s['date'], '%Y-%m-%d').date() <= week_end
        ]

    center_shifts_sorted = sorted(center_shifts, key=lambda x: (x['date'], x['worker_id']))

    cfg = get_requirements_config()
    weekly_min_workers = build_weekly_min_workers_map(center_id)

    check_rows = []
    worker_issues = defaultdict(list)

    shifts_by_day_type = defaultdict(list)
    shifts_by_worker = defaultdict(list)
    shifts_by_day = defaultdict(list)
    for s in center_shifts_sorted:
        day = datetime.strptime(s['date'], '%Y-%m-%d').date()
        shifts_by_day_type[(day, s['type'])].append(s['worker_id'])
        shifts_by_worker[s['worker_id']].append(s)
        shifts_by_day[day].append(s)

    # 1) Cierre los lunes
    monday_violations = []
    if cfg['monday_closed']:
        for s in center_shifts_sorted:
            day = datetime.strptime(s['date'], '%Y-%m-%d').date()
            if day.weekday() == 0 and s['type'] not in ['L', 'V', 'B']:
                monday_violations.append(s)
                worker_issues[s['worker_id']].append('Trabaja en lunes cerrado')
    check_rows.append({
        'Requisito': 'Cierre de sedes los lunes',
        'Estado': 'OK' if not monday_violations else 'INCUMPLE',
        'Detalle': f"{len(monday_violations)} turnos encontrados en lunes"
    })

    # 2) Verano solo mañana
    summer_violations = []
    if cfg['summer_only_morning']:
        for s in center_shifts_sorted:
            day = datetime.strptime(s['date'], '%Y-%m-%d').date()
            if is_summer_date(day) and s['type'] in ['T', 'N']:
                summer_violations.append(s)
                worker_issues[s['worker_id']].append('Turno tarde/noche en periodo de verano')
    check_rows.append({
        'Requisito': 'Verano solo turno de mañana',
        'Estado': 'OK' if not summer_violations else 'INCUMPLE',
        'Detalle': f"{len(summer_violations)} turnos fuera de regla"
    })

    # 3) Minimo trabajadores por turno (admite override semanal por sede)
    min_worker_violations = []
    all_days = sorted(shifts_by_day.keys())
    for day in all_days:
        week_key = f"{day.isocalendar().year}-W{day.isocalendar().week:02d}"
        required = weekly_min_workers.get(week_key, cfg['min_workers_per_shift'])
        expected_types = ['M'] if is_summer_date(day) else ['M', 'T']
        for t in expected_types:
            assigned = len(shifts_by_day_type.get((day, t), []))
            if assigned < required:
                min_worker_violations.append((day, t, assigned, required))
    check_rows.append({
        'Requisito': 'Minimo de trabajadores por turno',
        'Estado': 'OK' if not min_worker_violations else 'INCUMPLE',
        'Detalle': f"{len(min_worker_violations)} dias/turnos por debajo del minimo"
    })

    # 4) Descansos semanales por trabajador (exactos)
    weekly_rest_violations = 0
    required_rest_days = max(2, cfg['weekly_rest_days'])
    for worker_id, w_shifts in shifts_by_worker.items():
        worked_by_day = defaultdict(str)
        for s in w_shifts:
            day = datetime.strptime(s['date'], '%Y-%m-%d').date()
            worked_by_day[day] = s['type']

        if week_start is not None:
            week_ranges = [(week_start, week_start + timedelta(days=6))]
        else:
            available_days = sorted(worked_by_day.keys())
            week_ranges = []
            seen_weeks = set()
            for d in available_days:
                ws = d - timedelta(days=d.weekday())
                if ws not in seen_weeks:
                    seen_weeks.add(ws)
                    week_ranges.append((ws, ws + timedelta(days=6)))

        for ws, we in week_ranges:
            rest_days = 0
            for offset in range(7):
                curr_day = ws + timedelta(days=offset)
                day_shift = worked_by_day.get(curr_day, 'L')
                if day_shift in ['L', 'V', 'B', '']:
                    rest_days += 1
            if rest_days != required_rest_days:
                weekly_rest_violations += 1
                worker_issues[worker_id].append(
                    f"Descansos semanales distintos de {required_rest_days} en semana {get_week_label(ws)}"
                )

    check_rows.append({
        'Requisito': f"Descansos semanales exactos ({required_rest_days} dias)",
        'Estado': 'OK' if weekly_rest_violations == 0 else 'INCUMPLE',
        'Detalle': f"{weekly_rest_violations} semanas-trabajador con descanso distinto al criterio"
    })

    # 5) Descanso minimo entre jornadas
    rest_violations = 0
    for worker_id, w_shifts in shifts_by_worker.items():
        worked = [s for s in w_shifts if s['type'] in ['M', 'T', 'N']]
        worked = sorted(worked, key=lambda x: x['date'])
        previous_end = None
        for s in worked:
            day = datetime.strptime(s['date'], '%Y-%m-%d').date()
            start_dt, end_dt = shift_interval(day, s['type'])
            if previous_end and start_dt:
                rest_hours = (start_dt - previous_end).total_seconds() / 3600
                if rest_hours < cfg['minimum_rest_hours']:
                    rest_violations += 1
                    worker_issues[worker_id].append(f'Descanso insuficiente ({rest_hours:.1f}h)')
            if end_dt:
                previous_end = end_dt
    check_rows.append({
        'Requisito': f"Descanso minimo de {cfg['minimum_rest_hours']}h",
        'Estado': 'OK' if rest_violations == 0 else 'INCUMPLE',
        'Detalle': f"{rest_violations} transiciones con descanso insuficiente"
    })

    # 6) Rotacion entre turnos
    rotation_violations = 0
    if cfg['rotation_required']:
        for worker_id, w_shifts in shifts_by_worker.items():
            types = {s['type'] for s in w_shifts if s['type'] in ['M', 'T', 'N']}
            worked_days = len([s for s in w_shifts if s['type'] in ['M', 'T', 'N']])
            if worked_days >= 4 and len(types) < 2:
                rotation_violations += 1
                worker_issues[worker_id].append('No existe rotacion de turnos')
    check_rows.append({
        'Requisito': 'Rotacion de turnos',
        'Estado': 'OK' if rotation_violations == 0 else 'INCUMPLE',
        'Detalle': f"{rotation_violations} trabajadores sin rotacion"
    })

    # 7) Limite anual de dias trabajados
    annual_limit_violations = 0
    for worker_id, w_shifts in shifts_by_worker.items():
        by_year = defaultdict(int)
        for s in w_shifts:
            if s['type'] in ['M', 'T', 'N', 'Mr', 'Tr']:
                year = datetime.strptime(s['date'], '%Y-%m-%d').year
                by_year[year] += 1
        for _, worked_days in by_year.items():
            if worked_days > cfg['max_work_days_year']:
                annual_limit_violations += 1
                worker_issues[worker_id].append(f'Supera el limite anual de {cfg["max_work_days_year"]} dias')
                break
    check_rows.append({
        'Requisito': f"Limite anual de {cfg['max_work_days_year']} dias",
        'Estado': 'OK' if annual_limit_violations == 0 else 'INCUMPLE',
        'Detalle': f"{annual_limit_violations} trabajadores superan el limite"
    })

    # 8) Compensacion domingos/festivos
    compensation_violations = 0
    if cfg['compensation_after_sunday_holiday']:
        shifts_by_worker_date = defaultdict(dict)
        for worker_id, w_shifts in shifts_by_worker.items():
            for s in w_shifts:
                day = datetime.strptime(s['date'], '%Y-%m-%d').date()
                shifts_by_worker_date[worker_id][day] = s['type']
        for worker_id, by_date in shifts_by_worker_date.items():
            for day, shift_type in by_date.items():
                if shift_type not in ['M', 'T', 'N', 'Mr', 'Tr']:
                    continue
                holidays = fixed_holidays_for_year(day.year)
                if day.weekday() == 6 or day in holidays:
                    has_compensation = False
                    for delta in range(1, 8):
                        next_day = day + timedelta(days=delta)
                        if by_date.get(next_day) in ['L', 'V', 'B']:
                            has_compensation = True
                            break
                    if not has_compensation:
                        compensation_violations += 1
                        worker_issues[worker_id].append('Sin compensacion tras domingo/festivo')
    check_rows.append({
        'Requisito': 'Compensacion por domingo/festivo',
        'Estado': 'OK' if compensation_violations == 0 else 'INCUMPLE',
        'Detalle': f"{compensation_violations} casos sin compensacion"
    })

    # 9) Cierre de festivos obligatorios
    holiday_close_violations = 0
    if cfg['mandatory_closed_holidays']:
        for day, day_shifts in shifts_by_day.items():
            if day in fixed_holidays_for_year(day.year):
                for s in day_shifts:
                    if s['type'] not in ['L', 'V', 'B']:
                        holiday_close_violations += 1
                        worker_issues[s['worker_id']].append('Turno asignado en festivo de cierre obligatorio')
    check_rows.append({
        'Requisito': 'Festivos de cierre obligatorio',
        'Estado': 'OK' if holiday_close_violations == 0 else 'INCUMPLE',
        'Detalle': f"{holiday_close_violations} turnos en festivos cerrados"
    })

    worker_rows = []
    for w in workers:
        user_shifts = [s for s in shifts_by_worker.get(w['id'], []) if s['type'] in ['M', 'T', 'N', 'Mr', 'Tr']]
        hours = sum(SHIFT_TYPES.get(s['type'], {}).get('hours', 0) for s in user_shifts)
        issues = worker_issues.get(w['id'], [])
        worker_rows.append({
            'Usuario': f"{w['name']} {w['surname']}",
            'Cumple': 'SI' if len(issues) == 0 else 'NO',
            'Incidencias': len(issues),
            'Dias trabajados': len(user_shifts),
            'Horas': hours,
            'Detalle': ' | '.join(sorted(set(issues))) if issues else 'Sin incidencias'
        })

    checks_df = pd.DataFrame(check_rows)
    workers_df = pd.DataFrame(worker_rows)
    ok_checks = len(checks_df[checks_df['Estado'] == 'OK']) if not checks_df.empty else 0
    summary = {
        'ok_checks': ok_checks,
        'total_checks': len(check_rows),
        'workers_ok': len(workers_df[workers_df['Cumple'] == 'SI']) if not workers_df.empty else 0,
        'workers_total': len(workers_df)
    }
    return {
        'checks_df': checks_df,
        'workers_df': workers_df,
        'summary': summary,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'week_start': week_start.strftime('%Y-%m-%d') if week_start else '-',
        'week_end': (week_start + timedelta(days=6)).strftime('%Y-%m-%d') if week_start else '-',
        'week_label': get_week_label(week_start) if week_start else 'Todas las semanas'
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

        # Lunes cerrado para todos: obligatorio libre.
        model.Add(x[w, 0, 0] == 1)

        # Regla: No Tarde(2) o Noche(3) antes de Mañana(1) 
        for d in range(num_days - 1):
            model.AddImplication(x[w, d, 2], x[w, d+1, 1].Not())
            model.AddImplication(x[w, d, 3], x[w, d+1, 1].Not())
        # Descanso semanal exacto: 2 días libres.
        model.Add(sum(x[w, d, 0] for d in range(num_days)) == 2)

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
    menu = st.radio(
        "Menú",
        [
            "🏠 Inicio",
            "🏢 Sedes",
            "👥 Trabajadores",
            "🗓️ Cuadrante Semanal",
            "🤖 Generador IA",
            "✅ Verificación por Sede",
            "📚 Historial de Usuarios",
            "⚙️ Requisitos"
        ],
        label_visibility="collapsed"
    )
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
    if st.session_state.mysql_connected:
        st.success("Conectado a MySQL: los trabajadores se guardan en base de datos (visible en phpMyAdmin).")
    else:
        st.warning("MySQL no disponible: se guardará en memoria temporal de la sesión.")
        if st.button("Reintentar conexión MySQL"):
            ensure_mysql_ready()
            st.rerun()
        if st.session_state.mysql_last_error:
            st.caption(f"Detalle conexión MySQL: {st.session_state.mysql_last_error}")

    with st.form("new_worker"):
        col1, col2 = st.columns(2)
        name = col1.text_input("Nombre")
        surname = col2.text_input("Apellidos")
        center = st.selectbox("Sede Asignada", [c['name'] for c in st.session_state.db['centers']])
        role = st.selectbox("Rol", ["WORKER", "EDITOR", "ADMIN"])
        if st.form_submit_button("Registrar Trabajador"):
            c_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == center)
            new_w = {
                'id': next_worker_id(st.session_state.db['workers']),
                'name': name,
                'surname': surname,
                'center_id': c_id,
                'role': role
            }

            if st.session_state.mysql_connected:
                if insert_worker_mysql(new_w):
                    workers_db = load_workers_from_mysql()
                    if workers_db is not None: 
                        st.session_state.db['workers'] = workers_db
                    st.success("Trabajador registrado en MySQL.")
                else:
                    st.error("No se pudo guardar en MySQL. Revisa la conexión.")
            else:
                st.session_state.db['workers'].append(new_w)
                st.success("Trabajador registrado en sesión local.")
            
    st.write("### Plantilla")
    st.dataframe(pd.DataFrame(st.session_state.db['workers']), use_container_width=True)

    if st.session_state.db['workers']:
        st.write("### Editar o borrar trabajador")
        worker_labels = [f"{w['id']} - {w['name']} {w['surname']}" for w in st.session_state.db['workers']]
        selected_label = st.selectbox("Selecciona trabajador", worker_labels)
        selected_id = selected_label.split(" - ")[0]
        selected_worker = next(w for w in st.session_state.db['workers'] if w['id'] == selected_id)

        with st.form("edit_worker_form"):
            ec1, ec2 = st.columns(2)
            edit_name = ec1.text_input("Nombre (editar)", value=selected_worker['name'])
            edit_surname = ec2.text_input("Apellidos (editar)", value=selected_worker['surname'])
            center_names = [c['name'] for c in st.session_state.db['centers']]
            current_center_name = next(
                c['name'] for c in st.session_state.db['centers'] if c['id'] == selected_worker['center_id']
            )
            edit_center_name = st.selectbox(
                "Sede (editar)",
                center_names,
                index=center_names.index(current_center_name)
            )
            roles = ["WORKER", "EDITOR", "ADMIN"]
            edit_role = st.selectbox("Rol (editar)", roles, index=roles.index(selected_worker['role']))

            save_edit = st.form_submit_button("Guardar cambios trabajador")
            if save_edit:
                edit_center_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == edit_center_name)
                updated_worker = {
                    'id': selected_worker['id'],
                    'name': edit_name,
                    'surname': edit_surname,
                    'center_id': edit_center_id,
                    'role': edit_role
                }

                if st.session_state.mysql_connected:
                    if update_worker_mysql(updated_worker):
                        workers_db = load_workers_from_mysql()
                        if workers_db is not None:
                            st.session_state.db['workers'] = workers_db
                        st.success("Trabajador actualizado en MySQL.")
                        st.rerun()
                    else:
                        st.error("No se pudo actualizar en MySQL.")
                else:
                    for i, w in enumerate(st.session_state.db['workers']):
                        if w['id'] == selected_worker['id']:
                            st.session_state.db['workers'][i] = updated_worker
                            break
                    st.success("Trabajador actualizado en sesión local.")
                    st.rerun()

        if st.button("🗑️ Borrar trabajador seleccionado"):
            if st.session_state.mysql_connected:
                if delete_worker_mysql(selected_worker['id']):
                    workers_db = load_workers_from_mysql()
                    if workers_db is not None:
                        st.session_state.db['workers'] = workers_db
                    st.session_state.db['shifts'] = [
                        s for s in st.session_state.db['shifts'] if s['worker_id'] != selected_worker['id']
                    ]
                    st.success("Trabajador eliminado de MySQL.")
                    st.rerun()
                else:
                    st.error("No se pudo borrar en MySQL.")
            else:
                st.session_state.db['workers'] = [
                    w for w in st.session_state.db['workers'] if w['id'] != selected_worker['id']
                ]
                st.session_state.db['shifts'] = [
                    s for s in st.session_state.db['shifts'] if s['worker_id'] != selected_worker['id']
                ]
                st.success("Trabajador eliminado de la sesión local.")
                st.rerun()

elif menu == "🗓️ Cuadrante Semanal":
    st.title("Cuadrante Semanal")
    center_sel = st.selectbox("Filtrar por Sede", [c['name'] for c in st.session_state.db['centers']])
    c_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == center_sel)
    fecha_ref = st.date_input("Semana de referencia", value=datetime.now())
    week_start = get_week_start(fecha_ref)
    week_end = week_start + timedelta(days=6)
    st.caption(f"Semana visualizada: {week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')} ({get_week_label(week_start)})")

    if st.button("📄 Cargar horarios de ejemplo (PDF) para esta semana"):
        total_loaded = load_example_week_shifts(c_id, week_start)
        if total_loaded > 0:
            st.success(f"Se cargaron {total_loaded} turnos de ejemplo para la semana {get_week_label(week_start)}.")
            st.rerun()
        else:
            st.info("No se encontraron trabajadores de ejemplo para esta sede.")
    
    # Filtrar trabajadores y sus turnos
    workers_sede = [w for w in st.session_state.db['workers'] if w['center_id'] == c_id]
    
    if not workers_sede:
        st.warning("No hay trabajadores en esta sede.")
    else:
        num_dias = 7
        week_days = [week_start + timedelta(days=i) for i in range(num_dias)]
        
        data_roster = {}
        for w in workers_sede:
            nombre_full = f"{w['name']} {w['surname']}"
            data_roster[nombre_full] = [""] * num_dias
            for s in st.session_state.db['shifts']:
                if s['worker_id'] == w['id']:
                    shift_day = datetime.strptime(s['date'], '%Y-%m-%d').date()
                    if week_start <= shift_day <= week_end:
                        d_idx = (shift_day - week_start).days
                        data_roster[nombre_full][d_idx] = s['type']
        
        df_roster = pd.DataFrame(data_roster).T
        df_roster.columns = [f"{d.strftime('%a')} {d.strftime('%d/%m')}" for d in week_days]
        
        def color_roster(val):
            color = SHIFT_TYPES.get(val, {}).get('color', 'white')
            text_color = 'white' if val in ['N', 'T', 'B', 'V'] else 'black'
            return f'background-color: {color}; color: {text_color}; text-align: center; font-weight: bold'

        st.dataframe(df_roster.style.applymap(color_roster), use_container_width=True)
        st.markdown("**Leyenda del cuadrante**")
        st.markdown(
            "L = Libre | M = Mañana | T = Tarde | N = Noche | Mr = Mañana Reducida | Tr = Tarde Reducida | V = Vacaciones | B = Baja"
        )

elif menu == "🤖 Generador IA":
    st.title("Generador Automático de Horarios")
    st.info("Esta sección utiliza el motor lógico para rellenar los turnos vacíos cumpliendo todas las normativas.")
    
    sede_gen = st.selectbox("Seleccionar Sede para Generar", [c['name'] for c in st.session_state.db['centers']])
    fecha_inicio = st.date_input("Fecha de inicio (Lunes)", value=datetime.now())
    
    if st.button("🚀 Iniciar Generación de Turnos"):
        c_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == sede_gen)
        w_ids = [w['id'] for w in st.session_state.db['workers'] if w['center_id'] == c_id]
        week_start = get_week_start(fecha_inicio)
        week_end = week_start + timedelta(days=6)
        
        with st.spinner("Calculando cuadrante óptimo..."):
            nuevos_turnos = solver_automatico(w_ids, week_start)
            if nuevos_turnos:
                fechas_nuevas = {s['date'] for s in nuevos_turnos}
                st.session_state.db['shifts'] = [
                    s for s in st.session_state.db['shifts']
                    if not (s['worker_id'] in w_ids and s['date'] in fechas_nuevas)
                ]

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for s in nuevos_turnos:
                    s['source'] = 'IA'
                    s['created_at'] = timestamp

                st.session_state.db['shifts'].extend(nuevos_turnos)
                st.success(f"¡Generados {len(nuevos_turnos)} turnos con éxito!")

                verif = verify_center_requirements(c_id, week_start=week_start)
                st.session_state.last_verification_by_center[c_id] = verif
                st.session_state.db['verification_history'].append({
                    'timestamp': verif['generated_at'],
                    'center_id': c_id,
                    'week_label': verif['week_label'],
                    'week_start': week_start.strftime('%Y-%m-%d'),
                    'week_end': week_end.strftime('%Y-%m-%d'),
                    'ok_checks': verif['summary']['ok_checks'],
                    'total_checks': verif['summary']['total_checks'],
                    'workers_ok': verif['summary']['workers_ok'],
                    'workers_total': verif['summary']['workers_total']
                })
                st.info(
                    f"Verificación automática completada: "
                    f"{verif['summary']['ok_checks']}/{verif['summary']['total_checks']} requisitos OK | "
                    f"{verif['summary']['workers_ok']}/{verif['summary']['workers_total']} trabajadores cumplen | "
                    f"Semana: {verif['week_label']} ({verif['week_start']} a {verif['week_end']})"
                )
            else:
                st.error("No se pudo encontrar una solución válida con el personal actual.")

elif menu == "✅ Verificación por Sede":
    st.title("Verificación de Requisitos por Sede")
    st.markdown("Selecciona una sede para validar automáticamente los requisitos del checklist y ver el estado por trabajador.")

    sede_ver = st.selectbox("Sede para verificar", [c['name'] for c in st.session_state.db['centers']])
    c_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == sede_ver)
    semana_ver = st.date_input("Semana a verificar", value=datetime.now(), key="verify_week_date")
    week_start = get_week_start(semana_ver)
    week_end = week_start + timedelta(days=6)
    st.caption(f"Se verificará la semana {get_week_label(week_start)} ({week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')})")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        run_now = st.button("Verificar ahora")
    with col_b:
        use_last = st.button("Cargar última verificación")

    if run_now:
        verif = verify_center_requirements(c_id, week_start=week_start)
        st.session_state.last_verification_by_center[c_id] = verif
        st.session_state.db['verification_history'].append({
            'timestamp': verif['generated_at'],
            'center_id': c_id,
            'week_label': verif['week_label'],
            'week_start': verif['week_start'],
            'week_end': verif['week_end'],
            'ok_checks': verif['summary']['ok_checks'],
            'total_checks': verif['summary']['total_checks'],
            'workers_ok': verif['summary']['workers_ok'],
            'workers_total': verif['summary']['workers_total']
        })

    verif_data = st.session_state.last_verification_by_center.get(c_id)

    if verif_data:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Checks OK", f"{verif_data['summary']['ok_checks']}/{verif_data['summary']['total_checks']}")
        c2.metric("Trabajadores que cumplen", f"{verif_data['summary']['workers_ok']}/{verif_data['summary']['workers_total']}")
        c3.metric("Semana verificada", verif_data['week_label'])
        c4.metric("Estado general", "OK" if verif_data['summary']['ok_checks'] == verif_data['summary']['total_checks'] else "REVISAR")
        st.caption(f"Última ejecución: {verif_data['generated_at']} | Rango: {verif_data['week_start']} a {verif_data['week_end']}")

        st.subheader("Checklist de requisitos")
        st.dataframe(verif_data['checks_df'], use_container_width=True)

        st.subheader("Usuarios de la sede con verificación")
        st.dataframe(verif_data['workers_df'], use_container_width=True)
    else:
        st.warning("Aún no hay verificación guardada para esta sede. Pulsa 'Verificar ahora'.")

elif menu == "📚 Historial de Usuarios":
    st.title("Historial de Usuarios")
    st.markdown("Consulta el historial de turnos por sede y por trabajador.")

    sede_hist = st.selectbox("Sede", [c['name'] for c in st.session_state.db['centers']])
    c_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == sede_hist)

    workers_sede = [w for w in st.session_state.db['workers'] if w['center_id'] == c_id]
    worker_options = ['Todos'] + [f"{w['name']} {w['surname']}" for w in workers_sede]
    worker_selected = st.selectbox("Trabajador", worker_options)

    ids_filtrados = {w['id'] for w in workers_sede}
    if worker_selected != 'Todos':
        w_obj = next(w for w in workers_sede if f"{w['name']} {w['surname']}" == worker_selected)
        ids_filtrados = {w_obj['id']}

    rows_hist = []
    for s in st.session_state.db['shifts']:
        if s['worker_id'] in ids_filtrados:
            w = next(x for x in workers_sede if x['id'] == s['worker_id'])
            rows_hist.append({
                'Fecha': s['date'],
                'Usuario': f"{w['name']} {w['surname']}",
                'Turno': s['type'],
                'Horas': SHIFT_TYPES.get(s['type'], {}).get('hours', 0),
                'Origen': s.get('source', 'Manual'),
                'Creado': s.get('created_at', '-')
            })

    if rows_hist:
        df_hist = pd.DataFrame(rows_hist).sort_values(['Fecha', 'Usuario'])
        st.dataframe(df_hist, use_container_width=True)

        st.subheader("Resumen por usuario")
        resumen = df_hist.groupby('Usuario', as_index=False).agg(
            Turnos=('Turno', 'count'),
            Horas=('Horas', 'sum')
        )
        st.dataframe(resumen, use_container_width=True)
    else:
        st.info("No hay turnos registrados para el filtro seleccionado.")

    st.subheader("Historial de verificaciones")
    verif_rows = [
        v for v in st.session_state.db.get('verification_history', []) if v['center_id'] == c_id
    ]
    if verif_rows:
        df_ver_hist = pd.DataFrame(verif_rows)
        df_ver_hist['Sede'] = sede_hist
        cols = ['timestamp', 'Sede', 'week_label', 'week_start', 'week_end', 'ok_checks', 'total_checks', 'workers_ok', 'workers_total']
        cols_exist = [c for c in cols if c in df_ver_hist.columns]
        st.dataframe(df_ver_hist[cols_exist], use_container_width=True)
    else:
        st.caption("Sin verificaciones registradas todavía para esta sede.")

elif menu == "⚙️ Requisitos":
    st.title("Configuración de Requisitos")
    st.markdown("Define reglas globales y ajustes semanales por sede (cuando cambian por semana).")

    st.subheader("Requisitos globales")
    req_df = pd.DataFrame(st.session_state.db['requirements_global'])
    req_df = req_df[['key', 'description', 'enabled', 'value']]
    edited_req_df = st.data_editor(
        req_df,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            'key': st.column_config.TextColumn('Clave', disabled=True),
            'description': st.column_config.TextColumn('Descripción'),
            'enabled': st.column_config.CheckboxColumn('Activo'),
            'value': st.column_config.TextColumn('Valor')
        }
    )

    if st.button("Guardar requisitos globales"):
        st.session_state.db['requirements_global'] = edited_req_df.to_dict(orient='records')
        st.success("Requisitos globales actualizados.")

    st.subheader("Requisitos semanales por sede")
    with st.form('weekly_requirement_form'):
        col1, col2, col3 = st.columns(3)
        center_name = col1.selectbox('Sede', [c['name'] for c in st.session_state.db['centers']])
        week_key = col2.text_input('Semana (formato AAAA-W##)', value=f"{datetime.now().isocalendar().year}-W{datetime.now().isocalendar().week:02d}")
        min_workers = col3.number_input('Mínimo trabajadores por turno', min_value=1, max_value=10, value=2, step=1)
        notes = st.text_input('Notas')
        enabled = st.checkbox('Activo', value=True)
        submitted = st.form_submit_button('Añadir/Actualizar semana')

        if submitted:
            center_id = next(c['id'] for c in st.session_state.db['centers'] if c['name'] == center_name)
            updated = False
            for row in st.session_state.db['requirements_weekly']:
                if row['center_id'] == center_id and row['week_key'] == week_key:
                    row['min_workers_per_shift'] = int(min_workers)
                    row['notes'] = notes
                    row['enabled'] = enabled
                    updated = True
                    break
            if not updated:
                st.session_state.db['requirements_weekly'].append({
                    'center_id': center_id,
                    'week_key': week_key,
                    'min_workers_per_shift': int(min_workers),
                    'notes': notes,
                    'enabled': enabled
                })
            st.success('Requisito semanal guardado.')

    weekly_rows = []
    for row in st.session_state.db['requirements_weekly']:
        center_name = next((c['name'] for c in st.session_state.db['centers'] if c['id'] == row['center_id']), row['center_id'])
        weekly_rows.append({
            'Sede': center_name,
            'Semana': row['week_key'],
            'Min trabajadores': row['min_workers_per_shift'],
            'Activo': row.get('enabled', True),
            'Notas': row.get('notes', '')
        })

    if weekly_rows:
        st.dataframe(pd.DataFrame(weekly_rows), use_container_width=True)
    else:
        st.caption('No hay requisitos semanales definidos todavía.')

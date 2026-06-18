import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard de Seguridad", page_icon="🛡️", layout="wide")

# Menú lateral para subir los archivos
st.sidebar.header("📥 Carga de Datos")

# --- NUEVO: Campo para el nombre del cliente ---
cliente_manual = st.sidebar.text_input("🏢 Nombre del Cliente (Opcional)", placeholder="Ej. Homecenter")
st.sidebar.markdown("*(Si lo dejas en blanco, el sistema detectará la empresa por los correos).*")
# -----------------------------------------------

file_hist = st.sidebar.file_uploader("1. Subir Historial de Acceso", type=["xlsx"])
file_usr = st.sidebar.file_uploader("2. Subir Usuarios", type=["xlsx"])
file_llaves = st.sidebar.file_uploader("3. Subir Llaves", type=["xlsx"])

if file_hist and file_usr and file_llaves:
    with st.spinner('Procesando datos y configurando cliente...'):
        df_hist = pd.read_excel(file_hist)
        df_usr = pd.read_excel(file_usr)
        df_llaves = pd.read_excel(file_llaves)

        # --- NUEVO: Detección Automática de Cliente ---
        if cliente_manual:
            nombre_cliente = cliente_manual.upper()
        else:
            try:
                # Extraer el dominio del email (ej. de 'user@homecenter.co' saca 'homecenter.co')
                dominios = df_usr['Email'].dropna().str.split('@').str[1]
                # Filtrar correos de soporte propios (jonyco, sera4, gmail, etc.)
                dominios_reales = dominios[~dominios.str.contains('jonyco|sera4|gmail|hotmail|yahoo', na=False, case=False)]
                if not dominios_reales.empty:
                    # Toma el dominio más repetido y le quita el '.co' o '.com'
                    empresa_detectada = dominios_reales.mode()[0].split('.')[0].upper()
                    nombre_cliente = empresa_detectada
                else:
                    nombre_cliente = "EMPRESA CLIENTE"
            except:
                nombre_cliente = "EMPRESA CLIENTE"
        # ----------------------------------------------

        # Mostrar el título personalizado
        st.title(f"🛡️ Dashboard Interactivo de Seguridad - {nombre_cliente}")

        # Limpieza de datos (igual que antes)
        df_hist['Abierta'] = pd.to_datetime(df_hist['Abierta'], utc=True).dt.tz_convert('America/Bogota')
        df_hist['Fecha'] = df_hist['Abierta'].dt.date
        df_hist['Hora'] = df_hist['Abierta'].dt.hour
        df_hist['Usuario'] = df_hist['Usuario'].fillna("Virtual Pad / Sistema")
        df_hist['Nombre de la Cerradura'] = df_hist['Nombre de la Cerradura'].fillna("Desconocido")
        df_usr['Nombre Completo'] = (df_usr['Nombre'].fillna('') + ' ' + df_usr['Apellido'].fillna('')).str.strip()
        
        usuarios_con_actividad = set(df_hist['Usuario'].str.upper().unique())
        usuarios_sin_actividad = df_usr[~df_usr['Nombre Completo'].str.upper().isin(usuarios_con_actividad)]
        usuarios_sin_actividad = usuarios_sin_actividad[usuarios_sin_actividad['Estado'] != 'Eliminado']

        # KPIs
        activos = len(df_usr[df_usr['Estado'] != 'Eliminado'])
        admins = len(df_usr[(df_usr['Estado'] != 'Eliminado') & (df_usr['Grupo de Usuario'].isin(['Administradores', 'Administradores de Acceso']))])
        
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Usuarios en Plataforma", f"{activos}", f"{admins} Administradores")
        col2.metric("Candados Evaluados", f"{df_hist['Nombre de la Cerradura'].nunique()}")
        col3.metric("Aperturas Totales", f"{len(df_hist)}")
        col4.metric("Llaves Generadas", f"{len(df_llaves)}")
        st.markdown("---")

        # Selectores interactivos y Gráficos
        st.subheader("📈 Actividad Diaria por Tienda")
        tipo_grafico_diario = st.radio("Formato de gráfica:", ["Líneas de Tendencia", "Barras Agrupadas", "Área Apilada"], horizontal=True)
        df_daily = df_hist.groupby(['Fecha', 'Nombre de la Cerradura']).size().reset_index(name='Aperturas')
        
        if tipo_grafico_diario == "Líneas de Tendencia":
            fig_daily = px.line(df_daily, x='Fecha', y='Aperturas', color='Nombre de la Cerradura', markers=True)
        elif tipo_grafico_diario == "Barras Agrupadas":
            fig_daily = px.bar(df_daily, x='Fecha', y='Aperturas', color='Nombre de la Cerradura', barmode='group')
        else:
            fig_daily = px.area(df_daily, x='Fecha', y='Aperturas', color='Nombre de la Cerradura')
            
        fig_daily.update_xaxes(rangeslider_visible=True)
        st.plotly_chart(fig_daily, use_container_width=True)

        colA, colB = st.columns(2)
        with colA:
            st.subheader("⏰ Patrones Horarios")
            df_hourly = df_hist['Hora'].value_counts().sort_index().reset_index()
            df_hourly.columns = ['Hora', 'Aperturas']
            df_hourly['Color'] = ['#C00000' if h in [0,1,2,3,23] else '#4472C4' for h in df_hourly['Hora']]
            fig_hourly = go.Figure(data=[go.Bar(x=df_hourly['Hora'], y=df_hourly['Aperturas'], marker_color=df_hourly['Color'])])
            fig_hourly.update_layout(title="Rojo: Alertas fuera de horario (23h - 03h)")
            st.plotly_chart(fig_hourly, use_container_width=True)

        with colB:
            st.subheader("📍 Uso por Tienda")
            tipo_grafico_tienda = st.radio("Vista de tienda:", ["Gráfico de Pastel", "Gráfico de Barras"], horizontal=True)
            df_lock = df_hist['Nombre de la Cerradura'].value_counts().reset_index()
            df_lock.columns = ['Candado', 'Aperturas']
            if tipo_grafico_tienda == "Gráfico de Pastel":
                fig_lock = px.pie(df_lock, values='Aperturas', names='Candado', hole=0.4)
            else:
                fig_lock = px.bar(df_lock, x='Candado', y='Aperturas', color='Candado', text_auto=True)
            st.plotly_chart(fig_lock, use_container_width=True)

        st.subheader("🏆 Top Usuarios Más Activos")
        top_n = st.slider("Cantidad de usuarios a mostrar en el ranking:", min_value=5, max_value=30, value=15, step=5)
        df_top = df_hist['Usuario'].value_counts().head(top_n).reset_index()
        df_top.columns = ['Usuario', 'Aperturas']
        fig_top = px.bar(df_top, x='Aperturas', y='Usuario', orientation='h', color='Aperturas', color_continuous_scale='Blues')
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_top, use_container_width=True)

        st.markdown("---")
        st.subheader("🚨 Alertas de Seguridad: Ingresos fuera de horario")
        anomalias = df_hist[df_hist['Hora'].isin([0,1,2,3,23])][['Usuario', 'Nombre de la Cerradura', 'Abierta']]
        anomalias['Abierta'] = anomalias['Abierta'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(anomalias, use_container_width=True)

        st.subheader("👻 Riesgo: Usuarios con 0 Interacciones")
        st.dataframe(usuarios_sin_actividad[['Nombre Completo', 'Email', 'Grupo de Usuario']], use_container_width=True)

else:
    st.title("🛡️ Dashboard Interactivo de Seguridad")
    st.info("👈 Sube los 3 archivos de Excel en el panel izquierdo (Historial, Usuarios y Llaves) para comenzar el análisis.")

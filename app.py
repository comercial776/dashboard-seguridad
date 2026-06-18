import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Dashboard de Seguridad", page_icon="🛡️", layout="wide")
st.title("🛡️ Dashboard Interactivo de Seguridad - Prueba de Concepto")
st.markdown("Carga los archivos del sistema para generar automáticamente el informe gerencial interactivo.")

# Menú lateral para subir archivos
st.sidebar.header("📥 Carga de Datos")
file_hist = st.sidebar.file_uploader("1. Subir Historial de Acceso", type=["xlsx"])
file_usr = st.sidebar.file_uploader("2. Subir Usuarios", type=["xlsx"])
file_llaves = st.sidebar.file_uploader("3. Subir Llaves", type=["xlsx"])

if file_hist and file_usr and file_llaves:
    with st.spinner('Procesando datos de seguridad...'):
        # 1. Leer Datos
        df_hist = pd.read_excel(file_hist)
        df_usr = pd.read_excel(file_usr)
        df_llaves = pd.read_excel(file_llaves)

        # 2. Limpieza y Formato
        df_hist['Abierta'] = pd.to_datetime(df_hist['Abierta'], utc=True).dt.tz_convert('America/Bogota')
        df_hist['Fecha'] = df_hist['Abierta'].dt.date
        df_hist['Hora'] = df_hist['Abierta'].dt.hour
        df_hist['Usuario'] = df_hist['Usuario'].fillna("Virtual Pad / Sistema")
        df_hist['Nombre de la Cerradura'] = df_hist['Nombre de la Cerradura'].fillna("Desconocido")

        df_usr['Nombre Completo'] = (df_usr['Nombre'].fillna('') + ' ' + df_usr['Apellido'].fillna('')).str.strip()
        
        # Cruce para inactivos
        usuarios_con_actividad = set(df_hist['Usuario'].str.upper().unique())
        usuarios_sin_actividad = df_usr[~df_usr['Nombre Completo'].str.upper().isin(usuarios_con_actividad)]
        usuarios_sin_actividad = usuarios_sin_actividad[usuarios_sin_actividad['Estado'] != 'Eliminado']

        # 3. KPIs
        activos = len(df_usr[df_usr['Estado'] != 'Eliminado'])
        admins = len(df_usr[(df_usr['Estado'] != 'Eliminado') & (df_usr['Grupo de Usuario'].isin(['Administradores', 'Administradores de Acceso']))])
        
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Usuarios en Plataforma", f"{activos}", f"{admins} Administradores")
        col2.metric("Candados (Tiendas)", f"{df_hist['Nombre de la Cerradura'].nunique()}")
        col3.metric("Aperturas Totales", f"{len(df_hist)}")
        col4.metric("Llaves Generadas", f"{len(df_llaves)}")
        st.markdown("---")

        # 4. Gráficas
        st.subheader("📈 Actividad Diaria por Tienda")
        df_daily = df_hist.groupby(['Fecha', 'Nombre de la Cerradura']).size().reset_index(name='Aperturas')
        fig_daily = px.line(df_daily, x='Fecha', y='Aperturas', color='Nombre de la Cerradura', markers=True)
        fig_daily.update_xaxes(rangeslider_visible=True)
        st.plotly_chart(fig_daily, use_container_width=True)

        colA, colB = st.columns(2)
        with colA:
            st.subheader("⏰ Patrones Horarios")
            df_hourly = df_hist['Hora'].value_counts().sort_index().reset_index()
            df_hourly.columns = ['Hora', 'Aperturas']
            df_hourly['Color'] = ['#C00000' if h in [0,1,2,3,23] else '#4472C4' for h in df_hourly['Hora']]
            fig_hourly = go.Figure(data=[go.Bar(x=df_hourly['Hora'], y=df_hourly['Aperturas'], marker_color=df_hourly['Color'])])
            fig_hourly.update_layout(title="Rojo indica fuera de horario comercial (23h - 03h)")
            st.plotly_chart(fig_hourly, use_container_width=True)

        with colB:
            st.subheader("📍 Uso por Tienda")
            df_lock = df_hist['Nombre de la Cerradura'].value_counts().reset_index()
            df_lock.columns = ['Candado', 'Aperturas']
            fig_lock = px.pie(df_lock, values='Aperturas', names='Candado', hole=0.4)
            st.plotly_chart(fig_lock, use_container_width=True)

        # 5. Tablas Críticas
        st.subheader("🚨 Alertas de Seguridad: Ingresos fuera de horario")
        anomalias = df_hist[df_hist['Hora'].isin([0,1,2,3,23])][['Usuario', 'Nombre de la Cerradura', 'Abierta']]
        anomalias['Abierta'] = anomalias['Abierta'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(anomalias, use_container_width=True)

        st.subheader("🏆 Top 20 Usuarios Más Activos")
        df_top = df_hist['Usuario'].value_counts().head(20).reset_index()
        df_top.columns = ['Usuario', 'Aperturas']
        fig_top = px.bar(df_top, x='Aperturas', y='Usuario', orientation='h')
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_top, use_container_width=True)

        st.subheader("👻 Riesgo: Usuarios con 0 Interacciones")
        st.dataframe(usuarios_sin_actividad[['Nombre Completo', 'Email', 'Grupo de Usuario']], use_container_width=True)

else:
    st.info("👈 Sube los 3 archivos de Excel en el panel izquierdo para comenzar el análisis.")
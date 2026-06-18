import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Dashboard de Seguridad", page_icon="🛡️", layout="wide")
st.title("🛡️ Dashboard Interactivo de Seguridad - Prueba de Concepto")
st.markdown("Carga los archivos del sistema para generar el informe gerencial interactivo.")

# Menú lateral para subir los 3 archivos
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

        # 2. Limpieza de Fechas y Nombres
        df_hist['Abierta'] = pd.to_datetime(df_hist['Abierta'], utc=True).dt.tz_convert('America/Bogota')
        df_hist['Fecha'] = df_hist['Abierta'].dt.date
        df_hist['Hora'] = df_hist['Abierta'].dt.hour
        df_hist['Usuario'] = df_hist['Usuario'].fillna("Virtual Pad / Sistema")
        df_hist['Nombre de la Cerradura'] = df_hist['Nombre de la Cerradura'].fillna("Desconocido")

        df_usr['Nombre Completo'] = (df_usr['Nombre'].fillna('') + ' ' + df_usr['Apellido'].fillna('')).str.strip()
        
        # Cruce para detectar usuarios sin actividad
        usuarios_con_actividad = set(df_hist['Usuario'].str.upper().unique())
        usuarios_sin_actividad = df_usr[~df_usr['Nombre Completo'].str.upper().isin(usuarios_con_actividad)]
        usuarios_sin_actividad = usuarios_sin_actividad[usuarios_sin_actividad['Estado'] != 'Eliminado']

        # 3. Panel de KPIs Superiores
        activos = len(df_usr[df_usr['Estado'] != 'Eliminado'])
        admins = len(df_usr[(df_usr['Estado'] != 'Eliminado') & (df_usr['Grupo de Usuario'].isin(['Administradores', 'Administradores de Acceso']))])
        
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Usuarios en Plataforma", f"{activos}", f"{admins} Administradores")
        col2.metric("Candados Evaluados", f"{df_hist['Nombre de la Cerradura'].nunique()}")
        col3.metric("Aperturas Totales", f"{len(df_hist)}")
        col4.metric("Llaves Generadas", f"{len(df_llaves)}")
        st.markdown("---")

        # 4. GRÁFICAS INTERACTIVAS CON SELECTOR DE TIPO
        st.subheader("📈 Actividad Diaria por Tienda")
        
        # Opciones para que el usuario cambie el tipo de gráfico
        tipo_grafico_diario = st.radio("¿Cómo prefieres ver la actividad diaria?", ["Líneas de Tendencia", "Barras Agrupadas", "Área Apilada"], horizontal=True)
        
        df_daily = df_hist.groupby(['Fecha', 'Nombre de la Cerradura']).size().reset_index(name='Aperturas')
        
        # Lógica para intercambiar gráficos
        if tipo_grafico_diario == "Líneas de Tendencia":
            fig_daily = px.line(df_daily, x='Fecha', y='Aperturas', color='Nombre de la Cerradura', markers=True)
        elif tipo_grafico_diario == "Barras Agrupadas":
            fig_daily = px.bar(df_daily, x='Fecha', y='Aperturas', color='Nombre de la Cerradura', barmode='group')
        else:
            fig_daily = px.area(df_daily, x='Fecha', y='Aperturas', color='Nombre de la Cerradura')
            
        fig_daily.update_xaxes(rangeslider_visible=True)
        st.plotly_chart(fig_daily, use_container_width=True)

        # 5. GRÁFICOS SECUNDARIOS
        colA, colB = st.columns(2)
        with colA:
            st.subheader("⏰ Patrones Horarios")
            df_hourly = df_hist['Hora'].value_counts().sort_index().reset_index()
            df_hourly.columns = ['Hora', 'Aperturas']
            # Colorear de rojo las anomalías (23:00 a 03:59)
            df_hourly['Color'] = ['#C00000' if h in [0,1,2,3,23] else '#4472C4' for h in df_hourly['Hora']]
            fig_hourly = go.Figure(data=[go.Bar(x=df_hourly['Hora'], y=df_hourly['Aperturas'], marker_color=df_hourly['Color'])])
            fig_hourly.update_layout(title="Rojo: Alertas fuera de horario (23h - 03h)")
            st.plotly_chart(fig_hourly, use_container_width=True)

        with colB:
            st.subheader("📍 Uso por Tienda")
            # Selector para el gráfico de tienda
            tipo_grafico_tienda = st.radio("Vista de tienda:", ["Gráfico de Pastel", "Gráfico de Barras"], horizontal=True)
            df_lock = df_hist['Nombre de la Cerradura'].value_counts().reset_index()
            df_lock.columns = ['Candado', 'Aperturas']
            
            if tipo_grafico_tienda == "Gráfico de Pastel":
                fig_lock = px.pie(df_lock, values='Aperturas', names='Candado', hole=0.4)
            else:
                fig_lock = px.bar(df_lock, x='Candado', y='Aperturas', color='Candado', text_auto=True)
            st.plotly_chart(fig_lock, use_container_width=True)

        # 6. Top de Usuarios Dinámico
        st.subheader("🏆 Top Usuarios Más Activos")
        # Selector para elegir cuántos usuarios mostrar en el top
        top_n = st.slider("Cantidad de usuarios a mostrar en el ranking:", min_value=5, max_value=30, value=15, step=5)
        
        df_top = df_hist['Usuario'].value_counts().head(top_n).reset_index()
        df_top.columns = ['Usuario', 'Aperturas']
        fig_top = px.bar(df_top, x='Aperturas', y='Usuario', orientation='h', color='Aperturas', color_continuous_scale='Blues')
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_top, use_container_width=True)

        # 7. Tablas Críticas de Seguridad
        st.markdown("---")
        st.subheader("🚨 Alertas de Seguridad: Ingresos fuera de horario")
        anomalias = df_hist[df_hist['Hora'].isin([0,1,2,3,23])][['Usuario', 'Nombre de la Cerradura', 'Abierta']]
        anomalias['Abierta'] = anomalias['Abierta'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(anomalias, use_container_width=True)

        st.subheader("👻 Riesgo: Usuarios con 0 Interacciones")
        st.dataframe(usuarios_sin_actividad[['Nombre Completo', 'Email', 'Grupo de Usuario']], use_container_width=True)

else:
    st.info("👈 Sube los 3 archivos de Excel en el panel izquierdo (Historial, Usuarios y Llaves) para comenzar el análisis.")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re

# ==========================================
# CONFIGURAÇÃO VISUAL DA PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="Dashboard Executivo de Atendimentos", layout="wide")

st.markdown("""
    <style>
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        border-left: 5px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard Executivo de Atendimentos (Versão 11.0)")

# ==========================================
# OTIMIZAÇÃO DE MEMÓRIA (CACHE) E LIMPEZA
# ==========================================
@st.cache_data
def carregar_dados_atendimentos(ficheiro):
    df = pd.read_csv(ficheiro, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
    
    # Limpeza e Extração Inteligente de Cidade e Estado já no carregamento
    if 'Tag' in df.columns:
        df['Tag'] = df['Tag'].astype(str).str.upper().str.strip().str.replace('"', '')
        df['Tag'] = df['Tag'].replace('NAN', pd.NA)
        
        def extrair_cidade_estado(tag):
            if pd.isna(tag): return "Outros", "Não Identificado"
            match = re.search(r'([A-Z\sÁÉÍÓÚÂÊÔÃÕÇ]+?)\s*-\s*([A-Z]{2})', str(tag))
            if match:
                return match.group(1).strip(), match.group(2).strip()
            return "Outros", "Não Identificado"
            
        cidades, estados = zip(*df['Tag'].apply(extrair_cidade_estado))
        df['Cidade'] = cidades
        df['Estado'] = estados
        
    if 'Data de Entrada' in df.columns:
        df['Data de Entrada'] = pd.to_datetime(df['Data de Entrada'], dayfirst=True, errors='coerce')
        df['Hora'] = df['Data de Entrada'].dt.hour
        dias_pt = {'Monday': '1-Seg', 'Tuesday': '2-Ter', 'Wednesday': '3-Qua', 
                   'Thursday': '4-Qui', 'Friday': '5-Sex', 'Saturday': '6-Sáb', 'Sunday': '7-Dom'}
        df['Dia da Semana'] = df['Data de Entrada'].dt.day_name().map(dias_pt)
        
    return df

@st.cache_data
def carregar_dados_login(ficheiro):
    try:
        df = pd.read_csv(ficheiro, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
        if len(df.columns) <= 1:
            df = pd.read_csv(ficheiro, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
    except:
        df = pd.read_csv(ficheiro, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
    return df

def calcular_tempo_medio_e_segundos(serie_tempo):
    try:
        td = pd.to_timedelta(serie_tempo)
        media = td.mean()
        if pd.isna(media): return "00h 00m 00s", 0
        total_segundos = int(media.total_seconds())
        horas, resto = divmod(total_segundos, 3600)
        minutos, segundos = divmod(resto, 60)
        return f"{horas:02d}h {minutos:02d}m {segundos:02d}s", total_segundos
    except:
        return "N/A", 0

# ==========================================
# NAVEGAÇÃO SUPERIOR (ABAS) E MENU LATERAL
# ==========================================
aba_graficos, aba_auditoria = st.tabs(["📊 Gráficos e Análises", "🕵️ Auditoria de Jornada"])

st.sidebar.title("Configurações Gerais")

# ==========================================
# ABA 1: GRÁFICOS E ANÁLISES (ATENDIMENTOS)
# ==========================================
with aba_graficos:
    st.sidebar.markdown("### 📥 Dados de Atendimento")
    arq_atendimento = st.sidebar.file_uploader("Carregar Relatório de Atendimentos", type=['csv'], key="up_atend")
    
    st.sidebar.markdown("### 🎯 Metas (SLA)")
    meta_tempo_minutos = st.sidebar.number_input("Tempo Médio Ideal (minutos):", min_value=1, max_value=120, value=15)
    
    if arq_atendimento is not None:
        df = carregar_dados_atendimentos(arq_atendimento)
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filtros Globais")
        
        data_min, data_max = df['Data de Entrada'].min().date(), df['Data de Entrada'].max().date()
        datas_selecionadas = st.sidebar.date_input("Período:", value=(data_min, data_max), min_value=data_min, max_value=data_max, format="DD/MM/YYYY")
        
        if len(datas_selecionadas) == 2:
            data_inicio, data_fim = datas_selecionadas
            df_filtrado = df[(df['Data de Entrada'].dt.date >= data_inicio) & (df['Data de Entrada'].dt.date <= data_fim)]
        else:
            df_filtrado = df
            
        lista_status = df_filtrado['Status'].dropna().unique().tolist()
        status_selecionado = st.sidebar.multiselect("Status:", options=lista_status, default=lista_status)
        df_base = df_filtrado[df_filtrado['Status'].isin(status_selecionado)]
        
        # --- DESEMPENHO POR AGENTE ---
        st.markdown("### 👥 Desempenho por Agente")
        agentes = df_base['Agente'].value_counts().head(10).reset_index()
        agentes.columns = ['Agente', 'Quantidade']
        fig_agentes = px.bar(agentes, x='Quantidade', y='Agente', orientation='h', color='Quantidade')
        fig_agentes.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=30, b=0))
        
        eventos_agente = st.plotly_chart(fig_agentes, use_container_width=True, on_select="rerun", key="bar_agentes")
        agentes_clicados = [p["y"] for p in eventos_agente.get("selection", {}).get("points", [])]
        df_final = df_base[df_base['Agente'].isin(agentes_clicados)] if agentes_clicados else df_base
        
        st.divider()
        
        # --- MÉTRICAS ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Atendimentos", df_final.shape[0])
        col2.metric("Qtd. Agentes", df_final['Agente'].nunique())
        col3.metric("Qtd. Serviços", df_final['Serviço'].nunique())
        
        texto_tempo, segundos_totais = calcular_tempo_medio_e_segundos(df_final.get('Tempo de Atendimento', pd.Series()))
        minutos_reais = segundos_totais / 60
        diferenca_meta = meta_tempo_minutos - minutos_reais
        col4.metric(label="⏱️ Tempo Médio (vs Meta)", value=texto_tempo, delta=f"{diferenca_meta:.1f} min", delta_color="normal")
        
        st.divider()
        
        # --- TREEMAP (MAPA DE CIDADES INTERATIVO) ---
        st.markdown("### 🗺️ Mapa de Regiões de Chamados")
        st.info("💡 **Clique numa Cidade ou Estado abaixo** para atualizar os Horários de Pico apenas para essa região!")
        
        if not df_final.empty and 'Cidade' in df_final.columns:
            df_treemap = df_final.groupby(['Estado', 'Cidade']).size().reset_index(name='Volume')
            df_treemap = df_treemap[df_treemap['Estado'] != 'Não Identificado'] 
            
            fig_treemap = px.treemap(
                df_treemap, 
                path=[px.Constant("Brasil"), 'Estado', 'Cidade'], 
                values='Volume',
                color='Volume',
                color_continuous_scale='Blues'
            )
            # Mostra o nome e o número exato dentro do bloco!
            fig_treemap.update_traces(textinfo="label+value", root_color="lightgrey")
            fig_treemap.update_layout(margin=dict(t=30, l=0, r=0, b=0))
            
            eventos_mapa = st.plotly_chart(fig_treemap, use_container_width=True, on_select="rerun", key="treemap")
            
            # Captura a cidade ou estado que o usuário clicou
            locais_clicados = [p["label"] for p in eventos_mapa.get("selection", {}).get("points", [])]
        else:
            locais_clicados = []

        st.divider()
        
        # --- MAPA DE CALOR (HORÁRIOS DE PICO COM NÚMEROS) ---
        st.markdown("### 🔥 Mapa de Calor - Horários de Pico da Equipa")
        
        # Se o usuário clicou numa cidade, filtra os horários para ela!
        if locais_clicados:
            df_hora = df_final[(df_final['Estado'].isin(locais_clicados)) | (df_final['Cidade'].isin(locais_clicados))]
            st.success(f"A exibir horários de pico apenas para: **{', '.join(locais_clicados)}**")
        else:
            df_hora = df_final
            
        if not df_hora.empty and 'Hora' in df_hora.columns:
            df_heatmap = df_hora.groupby(['Dia da Semana', 'Hora']).size().reset_index(name='Volume')
            
            # text_auto=True escreve os números dentro do gráfico de forma clara!
            fig_calor = px.density_heatmap(
                df_heatmap, x='Hora', y='Dia da Semana', z='Volume',
                color_continuous_scale='YlOrRd', text_auto=True,
                labels={'Hora': 'Hora do Dia (0-23h)', 'Dia da Semana': 'Dia da Semana'}
            )
            fig_calor.update_yaxes(categoryorder='array', categoryarray=['7-Dom', '6-Sáb', '5-Sex', '4-Qui', '3-Qua', '2-Ter', '1-Seg'])
            # Aumenta um pouco a altura para ficar mais fácil de ler
            fig_calor.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0))
            
            st.plotly_chart(fig_calor, use_container_width=True)
            
    else:
        st.info("👈 Por favor, carregue o relatório de **Atendimentos** na barra lateral para ver os gráficos.")

# ==========================================
# ABA 2: AUDITORIA DE JORNADA (LOGIN)
# ==========================================
with aba_auditoria:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📥 Dados de Auditoria")
    arq_login = st.sidebar.file_uploader("Carregar Relatório de Login", type=['csv'], key="up_login")
    
    if arq_login is not None:
        df_login = carregar_dados_login(arq_login)
        st.markdown("### 🕵️ Auditoria de Jornada Individual")
        
        col1, col2, col3 = st.columns(3)
        col_nomes = col1.selectbox("Coluna dos Nomes:", options=df_login.columns.tolist(), index=0)
        col_inicio = col2.selectbox("Coluna de Login (Início):", options=df_login.columns.tolist(), index=1 if len(df_login.columns)>1 else 0)
        col_fim = col3.selectbox("Coluna de Logout (Fim):", options=df_login.columns.tolist(), index=2 if len(df_login.columns)>2 else 0)
        
        if col_nomes:
            lista_agentes = sorted(df_login[col_nomes].dropna().unique().tolist())
            agente_auditoria = st.selectbox("Selecione o Agente para Auditoria:", options=lista_agentes)
            
            if st.button("Gerar Auditoria Diária de 6 Horas"):
                df_agente = df_login[df_login[col_nomes] == agente_auditoria].copy()
                
                df_agente['DataInicio'] = pd.to_datetime(df_agente[col_inicio], dayfirst=True, errors='coerce')
                df_agente['DataFim'] = pd.to_datetime(df_agente[col_fim].replace('-', np.nan), dayfirst=True, errors='coerce')
                df_agente['DataFim'] = df_agente['DataFim'].fillna(df_agente['DataInicio'])
                
                df_agente['Dia'] = df_agente['DataInicio'].dt.date
                
                jornada = df_agente.groupby('Dia').agg(
                    Primeiro_Login=('DataInicio', 'min'),
                    Ultimo_Logout=('DataFim', 'max'),
                    Sessoes_no_Dia=('DataInicio', 'count')
                ).reset_index()
                
                jornada['Tempo_Logado_Total'] = jornada['Ultimo_Logout'] - jornada['Primeiro_Login']
                jornada['Cumpriu 6h?'] = jornada['Tempo_Logado_Total'].dt.total_seconds() >= 21600
                jornada['Cumpriu 6h?'] = jornada['Cumpriu 6h?'].map({True: '✅ Sim', False: '❌ Não (Menos de 6h)'})
                
                jornada['Dia'] = pd.to_datetime(jornada['Dia']).dt.strftime('%d/%m/%Y')
                jornada['Primeiro_Login'] = jornada['Primeiro_Login'].dt.strftime('%H:%M:%S')
                jornada['Ultimo_Logout'] = jornada['Ultimo_Logout'].dt.strftime('%H:%M:%S')
                
                def formatar_timedelta(td):
                    segundos = int(td.total_seconds())
                    horas, resto = divmod(segundos, 3600)
                    minutos, _ = divmod(resto, 60)
                    return f"{horas:02d}h {minutos:02d}m"
                    
                jornada['Tempo_Logado_Total'] = jornada['Tempo_Logado_Total'].apply(formatar_timedelta)
                
                jornada = jornada.rename(columns={
                    'Primeiro_Login': '1º Login do Dia', 
                    'Ultimo_Logout': 'Último Logout do Dia',
                    'Sessoes_no_Dia': 'Qtd. de Sessões'
                })
                
                st.dataframe(jornada, use_container_width=True, hide_index=True)
    else:
        st.info("👈 Por favor, carregue o relatório de **Login/Jornada** na barra lateral para usar a auditoria.")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Dashboard Interativo", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS VISUAIS CSS (UI/UX) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-left: 5px solid #2e66ff;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #f0f2f6;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #1f2937;
        font-weight: 700;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] {
        height: 55px;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #2e66ff !important;
        border-bottom: 3px solid #2e66ff !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard Analítico de Atendimentos")

# --- FUNÇÕES AUXILIARES ---
def calcular_tempo_medio(serie_tempo):
    try:
        td = pd.to_timedelta(serie_tempo)
        media = td.mean()
        if pd.isna(media): return "00h 00m 00s"
        total_segundos = int(media.total_seconds())
        horas, resto = divmod(total_segundos, 3600)
        minutos, segundos = divmod(resto, 60)
        return f"{horas:02d}h {minutos:02d}m {segundos:02d}s"
    except:
        return "N/A"

def formatar_timedelta_horas(td):
    if pd.isna(td): return "00h 00m"
    total_segundos = int(td.total_seconds())
    horas, resto = divmod(total_segundos, 3600)
    minutos, _ = divmod(resto, 60)
    return f"{horas:02d}h {minutos:02d}m"

# --- MENU LATERAL (AGORA COM DOIS UPLOADS) ---
st.sidebar.title("Configurações")
st.sidebar.markdown("### 📂 1. Dados de Atendimento")
arquivo_atendimentos = st.sidebar.file_uploader("Carregue o Relatório Analítico", type=['csv'], key="atend")

st.sidebar.markdown("### 📂 2. Dados de Login")
arquivo_login = st.sidebar.file_uploader("Carregue o Relatório de Login (Auditoria)", type=['csv'], key="login")

# ==========================================
# MENU SUPERIOR DE NAVEGAÇÃO (TABS)
# ==========================================
tab1, tab2 = st.tabs(["📊 Gráficos e Análises", "🕵️ Auditoria de Jornada (Login)"])

# ------------------------------------------
# ABA 1: GRÁFICOS E ANÁLISES (Requer Arquivo 1)
# ------------------------------------------
with tab1:
    if arquivo_atendimentos is not None:
        try:
            df = pd.read_csv(arquivo_atendimentos, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
            
            if 'Tag' in df.columns:
                df['Tag'] = df['Tag'].astype(str).str.upper().str.strip().str.replace('"', '')
                df['Tag'] = df['Tag'].replace('NAN', pd.NA)
                
            df['Data de Entrada'] = pd.to_datetime(df['Data de Entrada'], dayfirst=True, errors='coerce')
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("Filtros Globais (Atendimentos)")
            
            data_min = df['Data de Entrada'].dropna().min().date()
            data_max = df['Data de Entrada'].dropna().max().date()
            
            datas_selecionadas = st.sidebar.date_input(
                "Selecione o Período:", value=(data_min, data_max),
                min_value=data_min, max_value=data_max, format="DD/MM/YYYY"
            )
            
            if len(datas_selecionadas) == 2:
                data_inicio, data_fim = datas_selecionadas
                df_filtrado_data = df[(df['Data de Entrada'].dt.date >= data_inicio) & (df['Data de Entrada'].dt.date <= data_fim)]
            else:
                df_filtrado_data = df
            
            lista_status = df_filtrado_data['Status'].dropna().unique().tolist()
            status_selecionado = st.sidebar.multiselect("Selecione o Status:", options=lista_status, default=lista_status)
            
            df_base = df_filtrado_data[df_filtrado_data['Status'].isin(status_selecionado)]
            
            st.markdown("### Visão Geral da Equipa")
            st.info("💡 Clique numa barra para filtrar as caixas indicadoras em baixo por agente!")
            
            agentes = df_base['Agente'].value_counts().head(10).reset_index()
            agentes.columns = ['Agente', 'Quantidade']
            
            fig_agentes = px.bar(agentes, x='Quantidade', y='Agente', orientation='h', color='Quantidade', color_continuous_scale='Blues')
            fig_agentes.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0), coloraxis_showscale=False)
            fig_agentes.update_yaxes(categoryorder='total ascending', title='')
            fig_agentes.update_xaxes(title='', showgrid=True, gridcolor='#f0f2f6')
            
            eventos = st.plotly_chart(fig_agentes, use_container_width=True, on_select="rerun")
            
            agentes_clicados = []
            if "selection" in eventos and "points" in eventos["selection"]:
                for ponto in eventos["selection"]["points"]:
                    agentes_clicados.append(ponto["y"])
                    
            if len(agentes_clicados) > 0:
                df_final = df_base[df_base['Agente'].isin(agentes_clicados)]
            else:
                df_final = df_base
                
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Atendimentos", df_final.shape[0])
            col2.metric("Quantidade de Agentes", df_final['Agente'].nunique())
            col3.metric("Quantidade de Serviços", df_final['Serviço'].nunique())
            col4.metric("⏱️ Tempo Médio", calcular_tempo_medio(df_final['Tempo de Atendimento']))
            
            st.divider()
            
            colA, colB = st.columns(2)
            with colA:
                classificacoes = df_final['Classificação'].value_counts().head(10).reset_index()
                classificacoes.columns = ['Classificação', 'Quantidade']
                fig_class = px.bar(classificacoes, x='Quantidade', y='Classificação', orientation='h', title="Top 10 Classificações", color='Quantidade', color_continuous_scale='Teal')
                fig_class.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
                fig_class.update_yaxes(categoryorder='total ascending', title='')
                fig_class.update_xaxes(title='', showgrid=True, gridcolor='#f0f2f6')
                st.plotly_chart(fig_class, use_container_width=True)
                
            with colB:
                servicos = df_final['Serviço'].value_counts().head(10).reset_index()
                servicos.columns = ['Serviço', 'Quantidade']
                fig_servicos = px.bar(servicos, x='Quantidade', y='Serviço', orientation='h', title="Top 10 Serviços", color='Quantidade', color_continuous_scale='Purples')
                fig_servicos.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
                fig_servicos.update_yaxes(categoryorder='total ascending', title='')
                fig_servicos.update_xaxes(title='', showgrid=True, gridcolor='#f0f2f6')
                st.plotly_chart(fig_servicos, use_container_width=True)
                
        except Exception as e:
            st.error(f"Erro ao ler o ficheiro de Atendimentos. Detalhe: {e}")
    else:
        st.info("👈 Por favor, carregue o relatório de **Atendimentos** no menu lateral.")

# ------------------------------------------
# ABA 2: TEMPO LOGADO E AUDITORIA (Requer Arquivo 2)
# ------------------------------------------
with tab2:
    if arquivo_login is not None:
        try:
            # Tenta ler com ';' primeiro. Se falhar, tenta com ',' para evitar erros.
            try:
                df_login = pd.read_csv(arquivo_login, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
                if len(df_login.columns) == 1:
                    df_login = pd.read_csv(arquivo_login, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
            except:
                df_login = pd.read_csv(arquivo_login, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
                
            st.markdown("### Auditoria de Jornada Real (via Relatório de Login)")
            
            # Verificação inteligente de colunas
            colunas_disponiveis = df_login.columns.tolist()
            
            st.info("Verifique se as colunas abaixo foram identificadas corretamente pelo sistema:")
            
            col_x, col_y, col_z = st.columns(3)
            # Tentativa de adivinhar as colunas para facilitar para o usuário
            idx_agente = colunas_disponiveis.index('Agente') if 'Agente' in colunas_disponiveis else 0
            
            # O usuário pode alterar a coluna aqui se o arquivo tiver nomes diferentes
            coluna_agente = col_x.selectbox("Coluna do Nome/Agente:", colunas_disponiveis, index=idx_agente)
            coluna_inicio = col_y.selectbox("Coluna de Login/Entrada:", colunas_disponiveis, index=1 if len(colunas_disponiveis)>1 else 0)
            coluna_fim = col_z.selectbox("Coluna de Logout/Saída:", colunas_disponiveis, index=2 if len(colunas_disponiveis)>2 else 0)
            
            st.divider()
            
            # Tratamento dos dados de login baseados nas colunas selecionadas
            df_login[coluna_inicio] = pd.to_datetime(df_login[coluna_inicio], dayfirst=True, errors='coerce')
            df_login[coluna_fim] = pd.to_datetime(df_login[coluna_fim], dayfirst=True, errors='coerce')
            
            # Remove linhas com erros de data
            df_login_valido = df_login.dropna(subset=[coluna_inicio]).copy()
            df_login_valido['Dia'] = df_login_valido[coluna_inicio].dt.date
            
            # Calcula o tempo de cada sessão logada
            df_login_valido['Tempo_Sessao'] = df_login_valido[coluna_fim] - df_login_valido[coluna_inicio]
            
            agentes_disponiveis = sorted(df_login_valido[coluna_agente].dropna().unique().tolist())
            agente_auditoria = st.selectbox("Selecione um Agente para verificar a Jornada:", options=agentes_disponiveis)
            
            if agente_auditoria:
                df_agente = df_login_valido[df_login_valido[coluna_agente] == agente_auditoria]
                
                # Agrupa por dia, somando todo o tempo logado
                jornada = df_agente.groupby('Dia').agg(
                    Primeiro_Login=(coluna_inicio, 'min'),
                    Ultimo_Logout=(coluna_fim, 'max'),
                    Sessoes_Logadas=(coluna_inicio, 'count'),
                    Tempo_Total_Logado=('Tempo_Sessao', 'sum')
                ).reset_index()
                
                # Validação da meta de 6h (21600 segundos)
                jornada['Meta 6h'] = jornada['Tempo_Total_Logado'].dt.total_seconds() >= 21600
                jornada['Meta 6h'] = jornada['Meta 6h'].map({True: '✅ Cumpriu', False: '❌ Menos de 6h'})
                
                # Formatação visual
                jornada['Dia'] = pd.to_datetime(jornada['Dia']).dt.strftime('%d/%m/%Y')
                jornada['Primeiro_Login'] = jornada['Primeiro_Login'].dt.strftime('%H:%M:%S')
                jornada['Ultimo_Logout'] = jornada['Ultimo_Logout'].dt.strftime('%H:%M:%S')
                jornada['Tempo_Total_Logado'] = jornada['Tempo_Total_Logado'].apply(formatar_timedelta_horas)
                
                jornada = jornada.rename(columns={
                    'Primeiro_Login': 'Primeiro Login do Dia',
                    'Ultimo_Logout': 'Último Logout',
                    'Sessoes_Logadas': 'Qtd. Logins/Quedas',
                    'Tempo_Total_Logado': 'Tempo Efetivo Logado'
                })
                
                st.dataframe(jornada, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"Erro ao ler o ficheiro de Login. Verifique se escolheu as colunas certas. Detalhe: {e}")
    else:
        st.info("👈 Por favor, carregue o **Relatório de Login** no menu lateral para visualizar a Auditoria.")

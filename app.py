import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Dashboard Interativo Completo", layout="wide")

st.title("📊 Dashboard de Atendimentos - Versão 6.0 (Auditoria de Jornada)")

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

# --- MENU LATERAL ---
st.sidebar.title("Configurações")
st.sidebar.markdown("Faça o upload do ficheiro aqui:")
ficheiro_carregado = st.sidebar.file_uploader("", type=['csv'])

if ficheiro_carregado is not None:
    try:
        # Lendo os dados
        df = pd.read_csv(ficheiro_carregado, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
        
        # --- LIMPEZA DE DADOS ---
        if 'Tag' in df.columns:
            df['Tag'] = df['Tag'].astype(str).str.upper().str.strip().str.replace('"', '')
            df['Tag'] = df['Tag'].replace('NAN', pd.NA)
            
        # Preparando colunas de tempo
        df['Data de Entrada'] = pd.to_datetime(df['Data de Entrada'], dayfirst=True, errors='coerce')
        # Tenta pegar a data de finalização, se for '-', usa a data de entrada como fallback
        df['Data de finalização'] = pd.to_datetime(df['Data de finalização'].replace('-', np.nan), dayfirst=True, errors='coerce')
        df['Data de finalização'] = df['Data de finalização'].fillna(df['Data de Entrada'])
        df['Tempo em Fila (Segundos)'] = pd.to_timedelta(df['Tempo em Fila']).dt.total_seconds()
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filtros Globais")
        
        # Filtro de Data
        data_min = df['Data de Entrada'].min().date()
        data_max = df['Data de Entrada'].max().date()
        
        datas_selecionadas = st.sidebar.date_input(
            "Selecione o Período:", value=(data_min, data_max),
            min_value=data_min, max_value=data_max, format="DD/MM/YYYY"
        )
        
        if len(datas_selecionadas) == 2:
            data_inicio, data_fim = datas_selecionadas
            df_filtrado_data = df[(df['Data de Entrada'].dt.date >= data_inicio) & (df['Data de Entrada'].dt.date <= data_fim)]
        else:
            df_filtrado_data = df
        
        # Filtro de Status
        lista_status = df_filtrado_data['Status'].dropna().unique().tolist()
        status_selecionado = st.sidebar.multiselect("Selecione o Status:", options=lista_status, default=lista_status)
        
        df_base = df_filtrado_data[df_filtrado_data['Status'].isin(status_selecionado)]
        
        # --- VISÃO GERAL ---
        st.markdown("### 1. Visão Geral da Equipa")
        st.info("💡 Clique numa barra para filtrar as caixas indicadoras em baixo por agente!")
        
        agentes = df_base['Agente'].value_counts().head(10).reset_index()
        agentes.columns = ['Agente', 'Quantidade']
        fig_agentes = px.bar(agentes, x='Quantidade', y='Agente', orientation='h', color='Quantidade')
        
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
        col4.metric("⏱️ Tempo Médio de Atend.", calcular_tempo_medio(df_final['Tempo de Atendimento']))
        
        st.divider()
        
        # --- AUDITORIA DE JORNADA ---
        st.markdown("### 🕵️ 2. Auditoria de Jornada Individual")
        st.write("Analise o tempo de sistema de cada agente dia a dia, para verificar se estão a cumprir a carga horária e como está o tempo de espera dos seus clientes.")
        
        # Dropdown para escolher um agente específico
        lista_todos_agentes = sorted(df_base['Agente'].dropna().unique().tolist())
        agente_auditoria = st.selectbox("Selecione um Agente para a Auditoria:", options=lista_todos_agentes)
        
        if agente_auditoria:
            # Filtra os dados apenas para o agente selecionado
            df_auditoria = df_base[df_base['Agente'] == agente_auditoria].copy()
            df_auditoria['Dia'] = df_auditoria['Data de Entrada'].dt.date
            
            # Agrupa por dia para descobrir o primeiro e último horário do agente
            jornada = df_auditoria.groupby('Dia').agg(
                Primeiro_Atendimento=('Data de Entrada', 'min'),
                Ultimo_Atendimento=('Data de finalização', 'max'),
                Total_Atendimentos=('Data de Entrada', 'count'),
                Media_Espera=('Tempo em Fila (Segundos)', 'mean')
            ).reset_index()
            
            # Cálculos de tempo
            jornada['Tempo_Logado'] = jornada['Ultimo_Atendimento'] - jornada['Primeiro_Atendimento']
            
            # Verifica se cumpriu 6 horas (21600 segundos)
            jornada['Meta 6h'] = jornada['Tempo_Logado'].dt.total_seconds() >= 21600
            jornada['Meta 6h'] = jornada['Meta 6h'].map({True: '✅ Cumpriu', False: '❌ Menos de 6h'})
            
            # Formatação amigável para exibição
            jornada['Dia'] = pd.to_datetime(jornada['Dia']).dt.strftime('%d/%m/%Y')
            jornada['Primeiro_Atendimento'] = jornada['Primeiro_Atendimento'].dt.strftime('%H:%M:%S')
            jornada['Ultimo_Atendimento'] = jornada['Ultimo_Atendimento'].dt.strftime('%H:%M:%S')
            jornada['Tempo_Logado'] = jornada['Tempo_Logado'].apply(formatar_timedelta_horas)
            
            # Convertendo os segundos de espera para formato de tempo
            jornada['Media_Espera'] = pd.to_timedelta(jornada['Media_Espera'], unit='s').apply(
                lambda x: f"{int(x.total_seconds() // 60):02d}m {int(x.total_seconds() % 60):02d}s" if not pd.isna(x) else "00m 00s"
            )
            
            # Renomeando colunas para a tabela
            jornada = jornada.rename(columns={
                'Primeiro_Atendimento': 'Início do Turno',
                'Ultimo_Atendimento': 'Última Ação',
                'Total_Atendimentos': 'Qtd. Atendimentos',
                'Tempo_Logado': 'Tempo Logado (Calculado)',
                'Media_Espera': 'Tempo Médio em Fila (Espera)'
            })
            
            # Exibe a tabela bonitinha
            st.dataframe(jornada, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"Erro ao ler o ficheiro. Detalhe: {e}")
else:
    st.info("👈 Por favor, carregue o ficheiro CSV no menu ao lado para iniciar.")

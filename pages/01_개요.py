"""
개요 페이지 - 전체 혼잡도 요약
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.data import get_data, TIME_ORDER
from src.ui import render_filters, filter_data, show_data_info, render_page_header, show_congestion_legend, create_download_button

# 페이지 설정
st.set_page_config(
    page_title="개요 - 지하철 혼잡도",
    page_icon="📊",
    layout="wide"
)

def main():
    # 데이터 로드
    try:
        df = get_data()
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        st.stop()
    
    # 사이드바 필터
    filters = render_filters(df)
    
    # 데이터 필터링
    df_filtered = filter_data(df, filters)
    
    # 데이터 정보 표시
    show_data_info(df_filtered)
    
    # 페이지 헤더
    render_page_header(
        "📊 개요",
        "전체 지하철 혼잡도를 한눈에 파악할 수 있습니다."
    )
    
    # 혼잡도 범례
    show_congestion_legend()
    
    if len(df_filtered) == 0:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")
        return
    
    # KPI 카드
    st.subheader("🎯 주요 지표")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_congestion = df_filtered['congestion'].mean()
        st.metric("평균 혼잡도", f"{avg_congestion:.1f}%")
    
    with col2:
        max_congestion = df_filtered['congestion'].max()
        max_row = df_filtered.loc[df_filtered['congestion'].idxmax()]
        st.metric(
            "최대 혼잡도", 
            f"{max_congestion:.1f}%",
            delta=f"{max_row['station']}"
        )
    
    with col3:
        # 피크 시간대 (평균 혼잡도가 가장 높은 시간)
        time_avg = df_filtered.groupby('time_slot')['congestion'].mean()
        peak_time = time_avg.idxmax()
        st.metric("피크 시간대", peak_time, delta=f"{time_avg.max():.1f}%")
    
    with col4:
        st.metric("데이터 기준일", "2025-09-30")
    
    st.markdown("---")
    
    # 시간대별 전체 평균 라인 차트
    st.subheader("📈 시간대별 평균 혼잡도")
    
    # 시간대별 평균 계산
    time_stats = df_filtered.groupby('time_slot').agg({
        'congestion': ['mean', 'max', 'min']
    }).reset_index()
    time_stats.columns = ['time_slot', 'avg', 'max', 'min']
    
    # Plotly 라인 차트
    fig = go.Figure()
    
    # 평균 라인
    fig.add_trace(go.Scatter(
        x=time_stats['time_slot'].astype(str),
        y=time_stats['avg'],
        mode='lines+markers',
        name='평균',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=6),
        hovertemplate='<b>%{x}</b><br>평균: %{y:.1f}%<extra></extra>'
    ))
    
    # 최대값 라인 (반투명)
    fig.add_trace(go.Scatter(
        x=time_stats['time_slot'].astype(str),
        y=time_stats['max'],
        mode='lines',
        name='최대',
        line=dict(color='red', width=1, dash='dot'),
        opacity=0.5,
        hovertemplate='<b>%{x}</b><br>최대: %{y:.1f}%<extra></extra>'
    ))
    
    # 최소값 라인 (반투명)
    fig.add_trace(go.Scatter(
        x=time_stats['time_slot'].astype(str),
        y=time_stats['min'],
        mode='lines',
        name='최소',
        line=dict(color='green', width=1, dash='dot'),
        opacity=0.5,
        hovertemplate='<b>%{x}</b><br>최소: %{y:.1f}%<extra></extra>'
    ))
    
    # 피크 구간 강조 (출근 시간대: 07:00-09:00, 퇴근 시간대: 18:00-20:00)
    morning_peak = ['07:00', '07:30', '08:00', '08:30', '09:00']
    evening_peak = ['18:00', '18:30', '19:00', '19:30', '20:00']
    
    # 레이아웃 설정
    fig.update_layout(
        xaxis_title="시간대",
        yaxis_title="혼잡도 (%)",
        hovermode='x unified',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 통찰
    st.info(f"""
    💡 **통찰**: 
    - 가장 혼잡한 시간대는 **{peak_time}** (평균 {time_avg.max():.1f}%)입니다.
    - 전체 평균 혼잡도는 **{avg_congestion:.1f}%**입니다.
    """)
    
    st.markdown("---")
    
    # 혼잡 TOP 10 역
    st.subheader("🔴 혼잡 TOP 10 역")
    
    # 시간대 선택
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_time = st.selectbox(
            "시간대 선택",
            options=[str(t) for t in TIME_ORDER if t in df_filtered['time_slot'].values],
            index=0
        )
    
    with col2:
        top_n = st.number_input("표시 개수", min_value=5, max_value=30, value=10)
    
    # 선택한 시간대의 데이터 필터링
    df_time = df_filtered[df_filtered['time_slot'] == selected_time]
    
    if len(df_time) > 0:
        # 역+방향별로 그룹화하여 TOP N
        top_stations = df_time.nlargest(top_n, 'congestion')
        
        # 바 차트
        fig_bar = px.bar(
            top_stations,
            x='congestion',
            y=top_stations['station'] + ' (' + top_stations['direction'] + ')',
            orientation='h',
            color='congestion',
            color_continuous_scale='Reds',
            labels={'congestion': '혼잡도 (%)', 'y': ''},
            title=f"{selected_time} 시간대 혼잡 TOP {top_n}"
        )
        
        fig_bar.update_layout(
            height=max(400, top_n * 30),
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # 테이블
        with st.expander("📋 상세 데이터 보기"):
            display_df = top_stations[['line', 'station', 'direction', 'congestion']].copy()
            display_df.columns = ['호선', '역명', '방향', '혼잡도(%)']
            display_df['혼잡도(%)'] = display_df['혼잡도(%)'].round(1)
            st.dataframe(display_df, use_container_width=True)
            
            # 다운로드 버튼
            create_download_button(
                display_df,
                f"혼잡TOP_{selected_time.replace(':', '')}.csv",
                "📥 이 데이터 다운로드"
            )
    else:
        st.warning(f"{selected_time} 시간대의 데이터가 없습니다.")
    
    st.markdown("---")
    
    # 추가 통계
    st.subheader("📊 추가 통계")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 호선별 평균 혼잡도")
        line_avg = df_filtered.groupby('line')['congestion'].mean().sort_values(ascending=False)
        
        fig_line = px.bar(
            x=line_avg.values,
            y=line_avg.index,
            orientation='h',
            labels={'x': '평균 혼잡도 (%)', 'y': '호선'},
            color=line_avg.values,
            color_continuous_scale='Blues'
        )
        fig_line.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_line, use_container_width=True)
    
    with col2:
        st.markdown("#### 방향별 평균 혼잡도")
        dir_avg = df_filtered.groupby('direction')['congestion'].mean().sort_values(ascending=False)
        
        fig_dir = px.bar(
            x=dir_avg.values,
            y=dir_avg.index,
            orientation='h',
            labels={'x': '평균 혼잡도 (%)', 'y': '방향'},
            color=dir_avg.values,
            color_continuous_scale='Greens'
        )
        fig_dir.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_dir, use_container_width=True)


if __name__ == "__main__":
    main()

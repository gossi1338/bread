"""
역상세 페이지 - 특정 역의 상세 혼잡도 분석
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.data import get_data
from src.ui import (
    render_filters, filter_data, show_data_info,
    render_page_header, show_congestion_legend, create_download_button
)

# 페이지 설정
st.set_page_config(
    page_title="역상세 - 지하철 혼잡도",
    page_icon="🔍",
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
        "🔍 역 상세 분석",
        "특정 역의 시간대별 혼잡도 패턴을 상세히 분석합니다."
    )
    
    # 혼잡도 범례
    show_congestion_legend()
    
    if len(df_filtered) == 0:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")
        return
    
    # 역 검색/선택
    st.subheader("🚉 역 선택")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 역 목록 (호선 정보 포함)
        station_options = df_filtered.groupby(['station', 'line']).size().reset_index()[['station', 'line']]
        station_options['display'] = station_options['station'] + ' (' + station_options['line'] + ')'
        station_display_list = sorted(station_options['display'].unique())
        
        if len(station_display_list) == 0:
            st.error("분석할 역이 없습니다.")
            return
        
        selected_display = st.selectbox(
            "역 검색",
            options=station_display_list,
            index=0,
            help="역명을 입력하여 검색할 수 있습니다."
        )
        
        # 선택된 역과 호선 추출
        selected_station = selected_display.split(' (')[0]
        selected_line = selected_display.split(' (')[1].replace(')', '')
    
    # 선택한 역의 데이터
    df_station = df_filtered[
        (df_filtered['station'] == selected_station) & 
        (df_filtered['line'] == selected_line)
    ]
    
    if len(df_station) == 0:
        st.warning(f"{selected_station}역의 데이터가 없습니다.")
        return
    
    st.markdown("---")
    
    # 요약 카드
    st.subheader(f"📊 {selected_station}역 ({selected_line}) 요약")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_cong = df_station['congestion'].mean()
        st.metric("평균 혼잡도", f"{avg_cong:.1f}%")
    
    with col2:
        max_cong = df_station['congestion'].max()
        max_row = df_station.loc[df_station['congestion'].idxmax()]
        st.metric(
            "최대 혼잡도",
            f"{max_cong:.1f}%",
            delta=f"{max_row['direction']}"
        )
    
    with col3:
        peak_time = df_station.groupby('time_slot')['congestion'].mean().idxmax()
        st.metric("피크 시간대", peak_time)
    
    with col4:
        num_directions = df_station['direction'].nunique()
        st.metric("분석 방향", f"{num_directions}개")
    
    # 방향별 비교
    st.markdown("#### 방향별 평균 혼잡도 비교")
    dir_avg = df_station.groupby('direction')['congestion'].mean().sort_values(ascending=False)
    
    cols = st.columns(len(dir_avg))
    for idx, (direction, avg_val) in enumerate(dir_avg.items()):
        with cols[idx]:
            max_dir = df_station[df_station['direction'] == direction]['congestion'].max()
            st.metric(
                direction,
                f"{avg_val:.1f}%",
                delta=f"최대 {max_dir:.1f}%"
            )
    
    st.markdown("---")
    
    # 시간대별 혼잡도 라인 차트
    st.subheader(f"📈 {selected_station}역 시간대별 혼잡도")
    
    # 방향별 시간대 데이터
    time_data = df_station.groupby(['time_slot', 'direction'])['congestion'].mean().reset_index()
    
    # Plotly 라인 차트
    fig = go.Figure()
    
    directions = df_station['direction'].unique()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for idx, direction in enumerate(directions):
        dir_data = time_data[time_data['direction'] == direction]
        
        fig.add_trace(go.Scatter(
            x=dir_data['time_slot'].astype(str),
            y=dir_data['congestion'],
            mode='lines+markers',
            name=direction,
            line=dict(color=colors[idx % len(colors)], width=3),
            marker=dict(size=6),
            hovertemplate=f'<b>{direction}</b><br>시간: %{{x}}<br>혼잡도: %{{y:.1f}}%<extra></extra>'
        ))
        
        # 피크 구간 강조 (혼잡도 > 평균 + 표준편차)
        avg = dir_data['congestion'].mean()
        std = dir_data['congestion'].std()
        threshold = avg + std
        
        peak_data = dir_data[dir_data['congestion'] > threshold]
        if len(peak_data) > 0:
            fig.add_trace(go.Scatter(
                x=peak_data['time_slot'].astype(str),
                y=peak_data['congestion'],
                mode='markers',
                name=f'{direction} 피크',
                marker=dict(
                    size=12,
                    color=colors[idx % len(colors)],
                    symbol='star',
                    line=dict(width=2, color='white')
                ),
                showlegend=False,
                hovertemplate=f'<b>{direction} 피크</b><br>시간: %{{x}}<br>혼잡도: %{{y:.1f}}%<extra></extra>'
            ))
    
    # 평균선 추가
    overall_avg = df_station.groupby('time_slot')['congestion'].mean()
    fig.add_trace(go.Scatter(
        x=overall_avg.index.astype(str),
        y=overall_avg.values,
        mode='lines',
        name='전체 평균',
        line=dict(color='gray', width=2, dash='dash'),
        opacity=0.5,
        hovertemplate='<b>전체 평균</b><br>시간: %{x}<br>혼잡도: %{y:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        xaxis_title="시간대",
        yaxis_title="혼잡도 (%)",
        hovermode='x unified',
        height=500,
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
    insights = []
    for direction in directions:
        dir_data = df_station[df_station['direction'] == direction]
        dir_peak_time = dir_data.groupby('time_slot')['congestion'].mean().idxmax()
        dir_peak_val = dir_data.groupby('time_slot')['congestion'].mean().max()
        insights.append(f"**{direction}**: {dir_peak_time} ({dir_peak_val:.1f}%)")
    
    st.info("💡 **방향별 피크 시간대**\n" + " | ".join(insights))
    
    st.markdown("---")
    
    # 혼잡 시간대 TOP 3
    st.subheader(f"🔴 가장 혼잡한 시간대 TOP 3")
    
    col1, col2 = st.columns(2)
    
    for idx, direction in enumerate(directions):
        with col1 if idx % 2 == 0 else col2:
            st.markdown(f"#### {direction}")
            
            dir_data = df_station[df_station['direction'] == direction]
            top3 = dir_data.nlargest(3, 'congestion')[['time_slot', 'congestion']]
            
            for rank, (_, row) in enumerate(top3.iterrows(), 1):
                color = "🔴" if rank == 1 else "🟠" if rank == 2 else "🟡"
                st.markdown(f"{color} **{rank}위**: {row['time_slot']} - {row['congestion']:.1f}%")
    
    st.markdown("---")
    
    # 상세 데이터 테이블
    st.subheader(f"📋 {selected_station}역 상세 데이터")
    
    # 방향 선택
    table_direction = st.radio(
        "표시할 방향",
        options=['전체'] + list(directions),
        horizontal=True,
        key="table_dir"
    )
    
    if table_direction == '전체':
        table_data = df_station.copy()
    else:
        table_data = df_station[df_station['direction'] == table_direction].copy()
    
    # 테이블용 데이터 정리
    display_data = table_data[['time_slot', 'direction', 'congestion']].copy()
    display_data = display_data.sort_values(['direction', 'time_slot'])
    display_data['congestion'] = display_data['congestion'].round(1)
    display_data.columns = ['시간대', '방향', '혼잡도(%)']
    
    # 테이블 표시
    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # 통계 정보
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"총 {len(display_data)}개 데이터")
    with col2:
        st.caption(f"평균: {display_data['혼잡도(%)'].mean():.1f}%")
    with col3:
        st.caption(f"최대: {display_data['혼잡도(%)'].max():.1f}%")
    
    # CSV 다운로드
    create_download_button(
        display_data,
        f"{selected_station}역_{table_direction}_상세.csv",
        "📥 상세 데이터 다운로드"
    )
    
    st.markdown("---")
    
    # 시간대별 비교 (Pivot 형태)
    with st.expander("📊 시간대별 방향 비교 테이블"):
        st.markdown("#### 시간대 x 방향 비교")
        
        # 피벗 테이블 생성
        pivot_data = df_station.pivot_table(
            index='time_slot',
            columns='direction',
            values='congestion',
            aggfunc='mean'
        )
        
        # 스타일링
        def color_congestion(val):
            if pd.isna(val):
                return ''
            if val < 30:
                return 'background-color: #d4edda'
            elif val < 70:
                return 'background-color: #fff3cd'
            elif val < 130:
                return 'background-color: #f8d7da'
            else:
                return 'background-color: #f5c6cb; font-weight: bold'
        
        styled_pivot = pivot_data.style.applymap(color_congestion).format("{:.1f}")
        
        st.dataframe(styled_pivot, use_container_width=True, height=600)
        
        st.caption("색상: 🟢 여유(0-30%) | 🟡 보통(30-70%) | 🟠 혼잡(70-130%) | 🔴 매우혼잡(130%+)")
    
    # 히트맵
    with st.expander("🔥 시간대별 혼잡도 히트맵"):
        st.markdown("#### 시간대별 혼잡도 시각화")
        
        # 피벗 데이터 준비 (이미 위에서 생성)
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=pivot_data.T.values,
            x=pivot_data.index.astype(str),
            y=pivot_data.columns,
            colorscale='Reds',
            hovertemplate='시간: %{x}<br>방향: %{y}<br>혼잡도: %{z:.1f}%<extra></extra>'
        ))
        
        fig_heatmap.update_layout(
            xaxis_title="시간대",
            yaxis_title="방향",
            height=300,
            xaxis={'side': 'bottom', 'tickangle': -45}
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True)


if __name__ == "__main__":
    main()

"""
노선별 페이지 - 노선 단위 혼잡도 분석
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.data import get_data, get_unique_values, TIME_ORDER
from src.ui import (
    render_filters, filter_data, show_data_info, 
    render_page_header, show_congestion_legend, create_download_button
)

# 페이지 설정
st.set_page_config(
    page_title="노선별 - 지하철 혼잡도",
    page_icon="🚉",
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
        "🚉 노선별 분석",
        "각 노선의 혼잡도 패턴과 역별 비교를 제공합니다."
    )
    
    # 혼잡도 범례
    show_congestion_legend()
    
    if len(df_filtered) == 0:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")
        return
    
    # 노선 선택
    available_lines = sorted(df_filtered['line'].unique(), key=lambda x: int(x.replace('호선', '')) if '호선' in x else 999)
    
    if len(available_lines) == 0:
        st.error("분석할 노선이 없습니다.")
        return
    
    selected_line = st.selectbox(
        "🚇 분석할 노선 선택",
        options=available_lines,
        index=0
    )
    
    # 선택한 노선의 데이터
    df_line = df_filtered[df_filtered['line'] == selected_line]
    
    if len(df_line) == 0:
        st.warning(f"{selected_line}의 데이터가 없습니다.")
        return
    
    st.markdown("---")
    
    # 노선 요약 통계
    st.subheader(f"📊 {selected_line} 요약")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_cong = df_line['congestion'].mean()
        st.metric("평균 혼잡도", f"{avg_cong:.1f}%")
    
    with col2:
        max_cong = df_line['congestion'].max()
        st.metric("최대 혼잡도", f"{max_cong:.1f}%")
    
    with col3:
        num_stations = df_line['station'].nunique()
        st.metric("역 수", f"{num_stations}개")
    
    with col4:
        peak_time = df_line.groupby('time_slot')['congestion'].mean().idxmax()
        st.metric("피크 시간대", peak_time)
    
    st.markdown("---")
    
    # 시간대별 평균 라인 차트 (방향별)
    st.subheader(f"📈 {selected_line} 시간대별 평균 혼잡도")
    
    # 방향별 시간대 평균 계산
    time_dir_avg = df_line.groupby(['time_slot', 'direction'])['congestion'].mean().reset_index()
    
    # Plotly 라인 차트
    fig = px.line(
        time_dir_avg,
        x='time_slot',
        y='congestion',
        color='direction',
        markers=True,
        labels={'time_slot': '시간대', 'congestion': '혼잡도 (%)', 'direction': '방향'},
        title=f"{selected_line} 방향별 시간대 혼잡도"
    )
    
    fig.update_layout(
        height=400,
        hovermode='x unified',
        xaxis={'type': 'category'}
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 통찰
    directions = df_line['direction'].unique()
    insights = []
    for direction in directions:
        dir_data = df_line[df_line['direction'] == direction]
        dir_peak = dir_data.groupby('time_slot')['congestion'].mean().idxmax()
        dir_peak_val = dir_data.groupby('time_slot')['congestion'].mean().max()
        insights.append(f"**{direction}**: 피크 {dir_peak} ({dir_peak_val:.1f}%)")
    
    st.info("💡 **방향별 피크 시간대**\n" + " | ".join(insights))
    
    st.markdown("---")
    
    # 역별 피크 혼잡도 테이블
    st.subheader(f"🏆 {selected_line} 역별 혼잡도 순위")
    
    # 역+방향별 통계 계산
    station_stats = df_line.groupby(['station', 'direction']).agg({
        'congestion': ['max', 'mean']
    }).reset_index()
    station_stats.columns = ['station', 'direction', 'max_congestion', 'avg_congestion']
    
    # 피크 시간대 찾기
    peak_times = []
    for idx, row in station_stats.iterrows():
        station_dir_data = df_line[
            (df_line['station'] == row['station']) & 
            (df_line['direction'] == row['direction'])
        ]
        peak_time = station_dir_data.loc[station_dir_data['congestion'].idxmax(), 'time_slot']
        peak_times.append(peak_time)
    
    station_stats['peak_time'] = peak_times
    
    # 최대 혼잡도 기준 정렬
    station_stats = station_stats.sort_values('max_congestion', ascending=False)
    
    # 표시할 개수 선택
    col1, col2 = st.columns([3, 1])
    with col2:
        display_count = st.number_input("표시 개수", min_value=5, max_value=50, value=10, key="station_count")
    
    # 테이블 표시
    display_stats = station_stats.head(display_count).copy()
    display_stats['max_congestion'] = display_stats['max_congestion'].round(1)
    display_stats['avg_congestion'] = display_stats['avg_congestion'].round(1)
    display_stats.columns = ['역명', '방향', '최대혼잡도(%)', '평균혼잡도(%)', '피크시간']
    
    st.dataframe(
        display_stats,
        use_container_width=True,
        hide_index=True
    )
    
    # 다운로드 버튼
    create_download_button(
        display_stats,
        f"{selected_line.replace('호선', '호선_')}역별통계.csv",
        "📥 역별 통계 다운로드"
    )
    
    st.markdown("---")
    
    # 특정 시간대 역별 비교 바 차트
    st.subheader(f"⏰ 특정 시간대 역별 비교")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        available_times = sorted([str(t) for t in df_line['time_slot'].unique()])
        selected_time = st.selectbox(
            "시간대 선택",
            options=available_times,
            index=len(available_times) // 2 if available_times else 0,
            key="time_select"
        )
    
    with col2:
        show_direction = st.selectbox(
            "방향",
            options=['전체'] + list(df_line['direction'].unique()),
            key="dir_select"
        )
    
    # 선택한 시간대 데이터
    df_time_line = df_line[df_line['time_slot'] == selected_time]
    
    if show_direction != '전체':
        df_time_line = df_time_line[df_time_line['direction'] == show_direction]
    
    if len(df_time_line) > 0:
        # 역별 정렬 (혼잡도 높은 순)
        df_time_line = df_time_line.sort_values('congestion', ascending=True)
        
        # 바 차트
        if show_direction == '전체':
            # 방향별로 색상 구분
            fig_bar = px.bar(
                df_time_line,
                x='congestion',
                y='station',
                color='direction',
                orientation='h',
                labels={'congestion': '혼잡도 (%)', 'station': '역명', 'direction': '방향'},
                title=f"{selected_line} {selected_time} 역별 혼잡도",
                barmode='group'
            )
        else:
            fig_bar = px.bar(
                df_time_line,
                x='congestion',
                y='station',
                orientation='h',
                color='congestion',
                color_continuous_scale='Reds',
                labels={'congestion': '혼잡도 (%)', 'station': '역명'},
                title=f"{selected_line} {selected_time} {show_direction} 역별 혼잡도"
            )
        
        fig_bar.update_layout(
            height=max(400, len(df_time_line) * 20),
            showlegend=True if show_direction == '전체' else False
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # 가장 혼잡한 역 하이라이트
        max_station = df_time_line.loc[df_time_line['congestion'].idxmax()]
        st.success(f"🔴 가장 혼잡: **{max_station['station']}** ({max_station['direction']}) - {max_station['congestion']:.1f}%")
    else:
        st.warning(f"{selected_time} 시간대의 데이터가 없습니다.")
    
    st.markdown("---")
    
    # 히트맵 (역 x 시간대)
    with st.expander("🔥 역별 시간대 히트맵"):
        st.markdown(f"#### {selected_line} 역별 시간대 혼잡도 히트맵")
        
        # 방향 선택
        heatmap_direction = st.radio(
            "방향 선택",
            options=list(df_line['direction'].unique()),
            horizontal=True,
            key="heatmap_dir"
        )
        
        df_heatmap = df_line[df_line['direction'] == heatmap_direction]
        
        # 피벗 테이블 생성
        heatmap_data = df_heatmap.pivot_table(
            index='station',
            columns='time_slot',
            values='congestion',
            aggfunc='mean'
        )
        
        # Plotly 히트맵
        fig_heatmap = px.imshow(
            heatmap_data,
            labels=dict(x="시간대", y="역명", color="혼잡도(%)"),
            color_continuous_scale='Reds',
            aspect='auto'
        )
        
        fig_heatmap.update_layout(
            height=max(400, len(heatmap_data) * 20),
            xaxis={'side': 'bottom', 'tickangle': -45}
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True)


if __name__ == "__main__":
    main()

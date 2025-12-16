"""
히트맵 페이지 - 시간대별 혼잡도 히트맵 시각화
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
    page_title="히트맵 - 지하철 혼잡도",
    page_icon="🔥",
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
        "🔥 시간대별 히트맵",
        "노선별 역 x 시간대 혼잡도를 한눈에 파악합니다."
    )
    
    # 혼잡도 범례
    show_congestion_legend()
    
    if len(df_filtered) == 0:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")
        return
    
    # 노선 선택
    st.subheader("🚇 노선 및 옵션 선택")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        available_lines = sorted(
            df_filtered['line'].unique(),
            key=lambda x: int(x.replace('호선', '')) if '호선' in x else 999
        )
        
        if len(available_lines) == 0:
            st.error("표시할 노선이 없습니다.")
            return
        
        selected_line = st.selectbox(
            "노선 선택",
            options=available_lines,
            index=0,
            key="heatmap_line"
        )
    
    # 선택한 노선의 데이터
    df_line = df_filtered[df_filtered['line'] == selected_line]
    
    if len(df_line) == 0:
        st.warning(f"{selected_line}의 데이터가 없습니다.")
        return
    
    with col2:
        available_directions = df_line['direction'].unique()
        selected_direction = st.selectbox(
            "방향 선택",
            options=list(available_directions),
            index=0,
            key="heatmap_direction"
        )
    
    with col3:
        sort_options = ['역명순', '피크순', '평균순', '특정시간대순']
        sort_option = st.selectbox(
            "정렬 기준",
            options=sort_options,
            index=0,
            key="heatmap_sort"
        )
    
    # 특정 시간대 정렬 선택 시
    if sort_option == '특정시간대순':
        available_times = sorted([str(t) for t in df_line['time_slot'].unique()])
        default_idx = available_times.index('08:00') if '08:00' in available_times else 0
        sort_time = st.selectbox(
            "정렬 기준 시간대",
            options=available_times,
            index=default_idx,
            key="sort_time"
        )
    else:
        sort_time = None
    
    # 방향 필터 적용
    df_heatmap = df_line[df_line['direction'] == selected_direction]
    
    if len(df_heatmap) == 0:
        st.warning(f"{selected_direction} 방향의 데이터가 없습니다.")
        return
    
    st.markdown("---")
    
    # 피벗 테이블 생성
    heatmap_pivot = df_heatmap.pivot_table(
        index='station',
        columns='time_slot',
        values='congestion',
        aggfunc='mean'
    )
    
    # 정렬 적용
    if sort_option == '역명순':
        heatmap_pivot = heatmap_pivot.sort_index()
    elif sort_option == '피크순':
        # 각 역의 최대 혼잡도 기준 내림차순
        max_values = heatmap_pivot.max(axis=1)
        heatmap_pivot = heatmap_pivot.loc[max_values.sort_values(ascending=False).index]
    elif sort_option == '평균순':
        # 각 역의 평균 혼잡도 기준 내림차순
        mean_values = heatmap_pivot.mean(axis=1)
        heatmap_pivot = heatmap_pivot.loc[mean_values.sort_values(ascending=False).index]
    elif sort_option == '특정시간대순' and sort_time:
        # 특정 시간대 값 기준 내림차순
        if sort_time in heatmap_pivot.columns:
            heatmap_pivot = heatmap_pivot.sort_values(by=sort_time, ascending=False)
    
    # 히트맵 시각화
    st.subheader(f"📊 {selected_line} {selected_direction} 혼잡도 히트맵")
    
    # Plotly 히트맵
    fig = px.imshow(
        heatmap_pivot,
        labels=dict(x="시간대", y="역명", color="혼잡도(%)"),
        color_continuous_scale='Reds',
        aspect='auto',
        zmin=0,
        zmax=150
    )
    
    fig.update_layout(
        height=max(500, len(heatmap_pivot) * 25),
        xaxis={
            'side': 'bottom',
            'tickangle': -45,
            'tickmode': 'array',
            'tickvals': list(range(len(heatmap_pivot.columns))),
            'ticktext': [str(c) for c in heatmap_pivot.columns]
        },
        yaxis={'tickmode': 'array', 'tickvals': list(range(len(heatmap_pivot.index))), 'ticktext': list(heatmap_pivot.index)},
        coloraxis_colorbar=dict(
            title="혼잡도(%)",
            tickvals=[0, 30, 70, 100, 130, 150],
            ticktext=['0', '30', '70', '100', '130', '150+']
        )
    )
    
    fig.update_traces(
        hovertemplate='역: %{y}<br>시간: %{x}<br>혼잡도: %{z:.1f}%<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # 인사이트
    st.subheader("💡 인사이트")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 가장 혼잡한 구간 찾기
        max_val = heatmap_pivot.max().max()
        max_station = None
        max_time = None
        
        for station in heatmap_pivot.index:
            for time_slot in heatmap_pivot.columns:
                if heatmap_pivot.loc[station, time_slot] == max_val:
                    max_station = station
                    max_time = time_slot
                    break
            if max_station:
                break
        
        st.metric(
            "가장 혼잡한 구간",
            f"{max_station} {max_time}",
            delta=f"{max_val:.1f}%"
        )
    
    with col2:
        # 가장 여유로운 구간 (0 제외)
        min_val = heatmap_pivot[heatmap_pivot > 0].min().min()
        min_station = None
        min_time = None
        
        for station in heatmap_pivot.index:
            for time_slot in heatmap_pivot.columns:
                val = heatmap_pivot.loc[station, time_slot]
                if val == min_val and val > 0:
                    min_station = station
                    min_time = time_slot
                    break
            if min_station:
                break
        
        if min_station:
            st.metric(
                "가장 여유로운 구간",
                f"{min_station} {min_time}",
                delta=f"{min_val:.1f}%"
            )
    
    # 피크 시간대 분석
    st.markdown("#### 시간대별 평균 혼잡도")
    
    time_avg = heatmap_pivot.mean(axis=0)
    
    # 출근/퇴근 피크 찾기
    morning_times = ['07:00', '07:30', '08:00', '08:30', '09:00', '09:30']
    evening_times = ['17:30', '18:00', '18:30', '19:00', '19:30', '20:00']
    
    morning_peak = time_avg[[t for t in morning_times if t in time_avg.index]]
    evening_peak = time_avg[[t for t in evening_times if t in time_avg.index]]
    
    col1, col2 = st.columns(2)
    
    with col1:
        if len(morning_peak) > 0:
            peak_morning_time = morning_peak.idxmax()
            peak_morning_val = morning_peak.max()
            st.info(f"🌅 **출근 피크**: {peak_morning_time} (평균 {peak_morning_val:.1f}%)")
    
    with col2:
        if len(evening_peak) > 0:
            peak_evening_time = evening_peak.idxmax()
            peak_evening_val = evening_peak.max()
            st.info(f"🌆 **퇴근 피크**: {peak_evening_time} (평균 {peak_evening_val:.1f}%)")
    
    st.markdown("---")
    
    # 역별 통계 테이블
    st.subheader("📋 역별 혼잡도 통계")
    
    station_stats = pd.DataFrame({
        '역명': heatmap_pivot.index,
        '평균': heatmap_pivot.mean(axis=1).round(1),
        '최대': heatmap_pivot.max(axis=1).round(1),
        '최소': heatmap_pivot.min(axis=1).round(1),
        '피크시간': [heatmap_pivot.loc[s].idxmax() for s in heatmap_pivot.index]
    })
    
    # 최대값 기준 정렬
    station_stats = station_stats.sort_values('최대', ascending=False)
    
    st.dataframe(
        station_stats,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # 다운로드
    col1, col2 = st.columns(2)
    
    with col1:
        create_download_button(
            station_stats,
            f"{selected_line}_{selected_direction}_역별통계.csv",
            "📥 역별 통계 다운로드"
        )
    
    with col2:
        # 히트맵 데이터 다운로드
        download_data = heatmap_pivot.reset_index()
        create_download_button(
            download_data,
            f"{selected_line}_{selected_direction}_히트맵데이터.csv",
            "📥 히트맵 데이터 다운로드"
        )
    
    # 상세 데이터 테이블 (확장 패널)
    with st.expander("📊 상세 데이터 테이블"):
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
        
        styled_heatmap = heatmap_pivot.style.applymap(color_congestion).format("{:.1f}")
        
        st.dataframe(styled_heatmap, use_container_width=True, height=600)
        
        st.caption("색상: 🟢 여유(0-30%) | 🟡 보통(30-70%) | 🟠 혼잡(70-130%) | 🔴 매우혼잡(130%+)")


if __name__ == "__main__":
    main()

"""
비교 페이지 - 여러 역의 혼잡도 패턴 비교
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.data import get_data, TIME_ORDER
from src.ui import (
    render_filters, filter_data, show_data_info,
    render_page_header, show_congestion_legend, create_download_button
)

# 페이지 설정
st.set_page_config(
    page_title="비교 - 지하철 혼잡도",
    page_icon="🔀",
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
        "🔀 역 비교 분석",
        "여러 역의 혼잡도 패턴을 비교합니다."
    )
    
    # 혼잡도 범례
    show_congestion_legend()
    
    if len(df_filtered) == 0:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")
        return
    
    # 비교 대상 선택
    st.subheader("🎯 비교 대상 선택")
    
    # 역 목록 생성 (호선 정보 포함)
    station_options = df_filtered.groupby(['station', 'line']).size().reset_index()[['station', 'line']]
    station_options['display'] = station_options['station'] + ' (' + station_options['line'] + ')'
    station_display_list = sorted(station_options['display'].unique())
    
    if len(station_display_list) < 2:
        st.error("비교를 위해서는 최소 2개 이상의 역이 필요합니다.")
        return
    
    # 멀티 선택 (2~5개 제한)
    selected_stations = st.multiselect(
        "비교할 역 선택 (2~5개)",
        options=station_display_list,
        default=station_display_list[:2] if len(station_display_list) >= 2 else station_display_list,
        max_selections=5,
        help="최소 2개, 최대 5개까지 선택할 수 있습니다."
    )
    
    if len(selected_stations) < 2:
        st.warning("비교를 위해 최소 2개의 역을 선택해주세요.")
        return
    
    # 선택된 역 정보 파싱
    selected_info = []
    for display in selected_stations:
        station = display.split(' (')[0]
        line = display.split(' (')[1].replace(')', '')
        selected_info.append({'station': station, 'line': line, 'display': display})
    
    # 선택된 역의 데이터 필터링
    df_compare = pd.DataFrame()
    for info in selected_info:
        df_station = df_filtered[
            (df_filtered['station'] == info['station']) & 
            (df_filtered['line'] == info['line'])
        ].copy()
        df_station['display'] = info['display']
        df_compare = pd.concat([df_compare, df_station], ignore_index=True)
    
    if len(df_compare) == 0:
        st.warning("선택한 역의 데이터가 없습니다.")
        return
    
    # 선택된 역 표시
    st.markdown("**선택된 역:**")
    cols = st.columns(len(selected_stations))
    for idx, info in enumerate(selected_info):
        with cols[idx]:
            avg_cong = df_compare[df_compare['display'] == info['display']]['congestion'].mean()
            st.metric(info['display'], f"{avg_cong:.1f}%")
    
    st.markdown("---")
    
    # 방향 선택
    available_directions = df_compare['direction'].unique()
    
    col1, col2 = st.columns([3, 1])
    with col2:
        direction_option = st.selectbox(
            "방향 선택",
            options=['전체'] + list(available_directions),
            key="compare_direction"
        )
    
    # 방향 필터 적용
    if direction_option != '전체':
        df_compare_filtered = df_compare[df_compare['direction'] == direction_option]
    else:
        df_compare_filtered = df_compare.copy()
    
    # 시간대별 혼잡도 비교 라인 차트
    st.subheader("📈 시간대별 혼잡도 비교")
    
    # 역별 시간대 평균 계산
    time_compare = df_compare_filtered.groupby(['display', 'time_slot'])['congestion'].mean().reset_index()
    
    # Plotly 라인 차트
    fig_line = px.line(
        time_compare,
        x='time_slot',
        y='congestion',
        color='display',
        markers=True,
        labels={'time_slot': '시간대', 'congestion': '혼잡도 (%)', 'display': '역'},
        title="시간대별 혼잡도 비교"
    )
    
    fig_line.update_layout(
        height=450,
        hovermode='x unified',
        xaxis={'type': 'category'},
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig_line, use_container_width=True)
    
    # 인사이트
    insights = []
    for info in selected_info:
        station_data = time_compare[time_compare['display'] == info['display']]
        if len(station_data) > 0:
            peak_time = station_data.loc[station_data['congestion'].idxmax(), 'time_slot']
            peak_val = station_data['congestion'].max()
            insights.append(f"**{info['station']}**: {peak_time} ({peak_val:.1f}%)")
    
    if insights:
        st.info("💡 **역별 피크 시간대**\n" + " | ".join(insights))
    
    st.markdown("---")
    
    # 특정 시간대 비교
    st.subheader("⏰ 특정 시간대 비교")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        available_times = sorted([str(t) for t in df_compare_filtered['time_slot'].unique()])
        # 출퇴근 시간대 기본 선택 (08:00 또는 첫 번째)
        default_idx = available_times.index('08:00') if '08:00' in available_times else 0
        selected_time = st.selectbox(
            "시간대 선택",
            options=available_times,
            index=default_idx,
            key="compare_time"
        )
    
    # 선택한 시간대 데이터
    df_time_compare = df_compare_filtered[df_compare_filtered['time_slot'] == selected_time]
    
    if len(df_time_compare) > 0:
        # 역별 평균 계산 (같은 역에 여러 방향이 있을 수 있으므로)
        bar_data = df_time_compare.groupby('display')['congestion'].mean().reset_index()
        bar_data = bar_data.sort_values('congestion', ascending=True)
        
        # 막대 차트
        fig_bar = px.bar(
            bar_data,
            x='congestion',
            y='display',
            orientation='h',
            color='congestion',
            color_continuous_scale='Reds',
            labels={'congestion': '혼잡도 (%)', 'display': ''},
            title=f"{selected_time} 시간대 혼잡도 비교"
        )
        
        fig_bar.update_layout(
            height=max(300, len(bar_data) * 60),
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # 가장 혼잡한 역 표시
        max_row = bar_data.loc[bar_data['congestion'].idxmax()]
        min_row = bar_data.loc[bar_data['congestion'].idxmin()]
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🔴 가장 혼잡: **{max_row['display']}** - {max_row['congestion']:.1f}%")
        with col2:
            st.success(f"🟢 가장 여유: **{min_row['display']}** - {min_row['congestion']:.1f}%")
    else:
        st.warning(f"{selected_time} 시간대의 데이터가 없습니다.")
    
    st.markdown("---")
    
    # 피크 비교 테이블
    st.subheader("📋 피크 비교 테이블")
    
    # 역별 통계 계산
    compare_stats = []
    for info in selected_info:
        station_data = df_compare_filtered[df_compare_filtered['display'] == info['display']]
        
        if len(station_data) > 0:
            avg_cong = station_data['congestion'].mean()
            max_cong = station_data['congestion'].max()
            min_cong = station_data['congestion'].min()
            
            # 피크 시간대 찾기
            time_avg = station_data.groupby('time_slot')['congestion'].mean()
            peak_time = time_avg.idxmax() if len(time_avg) > 0 else '-'
            
            compare_stats.append({
                '역명': info['station'],
                '호선': info['line'],
                '평균 혼잡도(%)': round(avg_cong, 1),
                '최대 혼잡도(%)': round(max_cong, 1),
                '최소 혼잡도(%)': round(min_cong, 1),
                '피크 시간대': str(peak_time)
            })
    
    if compare_stats:
        df_stats = pd.DataFrame(compare_stats)
        
        # 최대 혼잡도 기준 정렬
        df_stats = df_stats.sort_values('최대 혼잡도(%)', ascending=False)
        
        st.dataframe(
            df_stats,
            use_container_width=True,
            hide_index=True
        )
        
        # 다운로드 버튼
        create_download_button(
            df_stats,
            "역비교_통계.csv",
            "📥 비교 통계 다운로드"
        )
    
    st.markdown("---")
    
    # 상세 데이터 (확장 패널)
    with st.expander("📊 상세 비교 데이터"):
        # 피벗 테이블: 시간대 x 역
        pivot_data = df_compare_filtered.pivot_table(
            index='time_slot',
            columns='display',
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
        
        st.dataframe(styled_pivot, use_container_width=True, height=500)
        
        st.caption("색상: 🟢 여유(0-30%) | 🟡 보통(30-70%) | 🟠 혼잡(70-130%) | 🔴 매우혼잡(130%+)")
        
        # 다운로드
        create_download_button(
            pivot_data.reset_index(),
            "역비교_시간대별.csv",
            "📥 시간대별 비교 데이터 다운로드"
        )


if __name__ == "__main__":
    main()

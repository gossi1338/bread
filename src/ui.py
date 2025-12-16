"""
공통 UI 컴포넌트 모듈
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any
from src.data import get_unique_values, get_stations_by_line, TIME_ORDER


def render_filters(df: pd.DataFrame) -> Dict[str, Any]:
    """
    사이드바에 필터를 렌더링하고 선택된 값을 반환합니다.
    
    Args:
        df: 데이터프레임
        
    Returns:
        dict: 필터 조건 딕셔너리
    """
    st.sidebar.header("🔍 필터")
    
    filters = {}
    
    # 1. 요일구분 선택
    day_types = get_unique_values(df, 'day_type')
    if day_types:
        filters['day_type'] = st.sidebar.radio(
            "요일 구분",
            options=day_types,
            index=0 if '평일' in day_types else 0
        )
    
    # 2. 호선 선택
    lines = get_unique_values(df, 'line')
    if lines:
        filters['lines'] = st.sidebar.multiselect(
            "호선 선택",
            options=lines,
            default=lines[:3] if len(lines) >= 3 else lines,
            help="복수 선택 가능합니다."
        )
    else:
        filters['lines'] = []
    
    # 3. 역 선택 (호선에 따라 동적으로 변경)
    if filters.get('lines'):
        # 선택된 호선들의 역 목록
        available_stations = []
        for line in filters['lines']:
            stations = get_stations_by_line(df, line)
            available_stations.extend(stations)
        available_stations = sorted(set(available_stations))
        
        if available_stations:
            filters['stations'] = st.sidebar.multiselect(
                "역 선택 (선택사항)",
                options=available_stations,
                default=[],
                help="특정 역만 보려면 선택하세요. 비어있으면 전체 역을 표시합니다."
            )
        else:
            filters['stations'] = []
    else:
        filters['stations'] = []
    
    # 4. 방향 선택
    directions = get_unique_values(df, 'direction')
    if directions:
        filters['directions'] = st.sidebar.multiselect(
            "방향 선택",
            options=directions,
            default=directions,
            help="상선/하선 또는 내선/외선"
        )
    else:
        filters['directions'] = []
    
    # 5. 시간대 범위 선택
    st.sidebar.markdown("### ⏰ 시간대 범위")
    
    time_indices = list(range(len(TIME_ORDER)))
    selected_range = st.sidebar.slider(
        "시간대 선택",
        min_value=0,
        max_value=len(TIME_ORDER) - 1,
        value=(0, len(TIME_ORDER) - 1),
        format="%d"
    )
    
    filters['time_range'] = (TIME_ORDER[selected_range[0]], TIME_ORDER[selected_range[1]])
    
    # 선택된 시간대 표시
    st.sidebar.caption(f"선택: {filters['time_range'][0]} ~ {filters['time_range'][1]}")
    
    # 6. 혼잡도 범위 선택 (선택사항)
    with st.sidebar.expander("🎚️ 혼잡도 범위 (고급)"):
        congestion_range = st.slider(
            "혼잡도 범위 (%)",
            min_value=0,
            max_value=200,
            value=(0, 200),
            help="특정 혼잡도 범위의 데이터만 필터링"
        )
        filters['congestion_range'] = congestion_range
    
    return filters


def filter_data(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """
    필터 조건에 따라 데이터를 필터링합니다.
    
    Args:
        df: 원본 데이터프레임
        filters: 필터 조건 딕셔너리
        
    Returns:
        pd.DataFrame: 필터링된 데이터프레임
    """
    df_filtered = df.copy()
    
    # 요일 구분
    if filters.get('day_type'):
        df_filtered = df_filtered[df_filtered['day_type'] == filters['day_type']]
    
    # 호선
    if filters.get('lines'):
        df_filtered = df_filtered[df_filtered['line'].isin(filters['lines'])]
    
    # 역 (선택된 경우만)
    if filters.get('stations'):
        df_filtered = df_filtered[df_filtered['station'].isin(filters['stations'])]
    
    # 방향
    if filters.get('directions'):
        df_filtered = df_filtered[df_filtered['direction'].isin(filters['directions'])]
    
    # 시간대 범위
    if filters.get('time_range'):
        start_time, end_time = filters['time_range']
        # Categorical이므로 문자열 비교가 아닌 범위 비교
        df_filtered = df_filtered[
            (df_filtered['time_slot'] >= start_time) & 
            (df_filtered['time_slot'] <= end_time)
        ]
    
    # 혼잡도 범위
    if filters.get('congestion_range'):
        min_cong, max_cong = filters['congestion_range']
        df_filtered = df_filtered[
            (df_filtered['congestion'] >= min_cong) & 
            (df_filtered['congestion'] <= max_cong)
        ]
    
    return df_filtered


def format_time_slot(time_str: str) -> str:
    """
    시간 슬롯 문자열을 보기 좋은 형태로 포맷합니다.
    
    Args:
        time_str: 시간 문자열 (예: "05:30")
        
    Returns:
        str: 포맷된 시간 문자열
    """
    return time_str


def display_metric_card(label: str, value: Any, delta: Optional[str] = None):
    """
    메트릭 카드를 표시합니다.
    
    Args:
        label: 레이블
        value: 값
        delta: 변화량 (선택사항)
    """
    st.metric(label=label, value=value, delta=delta)


def create_download_button(df: pd.DataFrame, filename: str, button_label: str = "📥 CSV 다운로드"):
    """
    데이터프레임을 CSV로 다운로드할 수 있는 버튼을 생성합니다.
    
    Args:
        df: 다운로드할 데이터프레임
        filename: 저장될 파일명
        button_label: 버튼 레이블
    """
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label=button_label,
        data=csv,
        file_name=filename,
        mime='text/csv'
    )


def show_data_info(df: pd.DataFrame):
    """
    데이터 정보를 사이드바에 표시합니다.
    
    Args:
        df: 데이터프레임
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 데이터 정보")
    st.sidebar.caption(f"총 데이터: {len(df):,}개")
    
    if len(df) > 0:
        st.sidebar.caption(f"호선 수: {df['line'].nunique()}개")
        st.sidebar.caption(f"역 수: {df['station'].nunique()}개")
        st.sidebar.caption(f"시간대 수: {df['time_slot'].nunique()}개")


def render_page_header(title: str, description: str = ""):
    """
    페이지 헤더를 렌더링합니다.
    
    Args:
        title: 페이지 제목
        description: 페이지 설명
    """
    st.title(title)
    if description:
        st.markdown(description)
    st.markdown("---")


def show_congestion_legend():
    """
    혼잡도 레벨에 대한 설명을 표시합니다.
    """
    with st.expander("💡 혼잡도 이해하기"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**🟢 여유**")
            st.caption("0-30%")
        
        with col2:
            st.markdown("**🟡 보통**")
            st.caption("30-70%")
        
        with col3:
            st.markdown("**🟠 혼잡**")
            st.caption("70-130%")
        
        with col4:
            st.markdown("**🔴 매우혼잡**")
            st.caption("130%+")
        
        st.info(
            "혼잡도는 열차 정원 대비 승객 수의 비율을 나타냅니다. "
            "100%는 모든 좌석이 찼고 일부 승객이 서 있는 상태이며, "
            "150% 이상은 매우 혼잡하여 승하차가 어려운 수준입니다."
        )


def get_congestion_color(congestion: float) -> str:
    """
    혼잡도에 따른 색상을 반환합니다.
    
    Args:
        congestion: 혼잡도 값
        
    Returns:
        str: 색상 코드
    """
    if congestion < 30:
        return '#4CAF50'  # 녹색 (여유)
    elif congestion < 70:
        return '#FFC107'  # 노란색 (보통)
    elif congestion < 130:
        return '#FF9800'  # 주황색 (혼잡)
    else:
        return '#F44336'  # 빨간색 (매우혼잡)

"""
서울교통공사 지하철 혼잡도 대시보드
메인 진입점
"""
import streamlit as st
from src.data import get_data
from src.ui import render_filters, filter_data, show_data_info, render_page_header, show_congestion_legend

# 페이지 설정
st.set_page_config(
    page_title="지하철 혼잡도 대시보드",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    h1 {
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# 메인 페이지
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
    
    # 메인 컨텐츠
    render_page_header(
        "🚇 서울교통공사 지하철 혼잡도 대시보드",
        "서울 지하철 혼잡도 데이터를 시각화하고 분석하는 대시보드입니다."
    )
    
    # 혼잡도 범례
    show_congestion_legend()
    
    # 안내 메시지
    st.info("👈 왼쪽 사이드바에서 페이지를 선택하세요.")
    
    # 주요 기능 소개
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📊 개요")
        st.markdown("""
        - 전체 혼잡도 요약
        - 시간대별 평균 추이
        - 혼잡 TOP 10 역
        """)
    
    with col2:
        st.markdown("### 🚉 노선별")
        st.markdown("""
        - 노선별 혼잡도 분석
        - 역별 피크 시간대
        - 시간대별 비교
        """)
    
    with col3:
        st.markdown("### 🔍 역상세")
        st.markdown("""
        - 특정 역 상세 분석
        - 방향별 혼잡도
        - 데이터 다운로드
        """)
    
    st.markdown("---")
    
    # 빠른 통계
    if len(df_filtered) > 0:
        st.subheader("📈 빠른 통계 (필터 적용)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_congestion = df_filtered['congestion'].mean()
            st.metric("평균 혼잡도", f"{avg_congestion:.1f}%")
        
        with col2:
            max_congestion = df_filtered['congestion'].max()
            st.metric("최대 혼잡도", f"{max_congestion:.1f}%")
        
        with col3:
            num_stations = df_filtered['station'].nunique()
            st.metric("분석 대상 역", f"{num_stations}개")
        
        with col4:
            num_lines = df_filtered['line'].nunique()
            st.metric("분석 대상 노선", f"{num_lines}개")
        
        # 가장 혼잡한 역/시간대
        st.markdown("### 🔴 가장 혼잡한 구간")
        
        max_row = df_filtered.loc[df_filtered['congestion'].idxmax()]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"""
            **역**: {max_row['station']} ({max_row['line']})  
            **방향**: {max_row['direction']}  
            **시간대**: {max_row['time_slot']}  
            **혼잡도**: {max_row['congestion']:.1f}%
            """)
        
        with col2:
            # 시간대별 평균 혼잡도 TOP 3
            time_avg = df_filtered.groupby('time_slot')['congestion'].mean().sort_values(ascending=False).head(3)
            
            st.markdown("**가장 혼잡한 시간대 TOP 3**")
            for idx, (time, cong) in enumerate(time_avg.items(), 1):
                st.caption(f"{idx}. {time} - {cong:.1f}%")
    else:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")
    
    # 데이터 출처
    st.markdown("---")
    st.caption("📅 데이터 기준일: 2025년 9월 30일")
    st.caption("📍 데이터 출처: 서울교통공사")


if __name__ == "__main__":
    main()

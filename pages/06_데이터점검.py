"""
데이터 점검 페이지 - 데이터 품질 및 이상치 확인
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from src.data import get_data, get_unique_values, TIME_ORDER
from src.ui import (
    render_filters, filter_data, show_data_info,
    render_page_header, create_download_button
)

# 페이지 설정
st.set_page_config(
    page_title="데이터 점검 - 지하철 혼잡도",
    page_icon="🔬",
    layout="wide"
)

def main():
    # 데이터 로드
    try:
        df = get_data()
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        st.stop()
    
    # 페이지 헤더
    render_page_header(
        "🔬 데이터 품질 점검",
        "데이터의 완전성과 이상치를 확인합니다."
    )
    
    # 전체 데이터 사용 (필터 없이)
    st.info("💡 이 페이지는 전체 데이터를 기준으로 품질을 점검합니다.")
    
    # 기본 통계
    st.subheader("📊 기본 통계")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("총 데이터 건수", f"{len(df):,}개")
    
    with col2:
        st.metric("호선 수", f"{df['line'].nunique()}개")
    
    with col3:
        st.metric("역 수", f"{df['station'].nunique()}개")
    
    with col4:
        st.metric("시간대 수", f"{df['time_slot'].nunique()}개")
    
    with col5:
        st.metric("방향 구분", f"{df['direction'].nunique()}개")
    
    st.markdown("---")
    
    # 데이터 품질 지표
    st.subheader("⚠️ 데이터 품질 지표")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # 결측값 분석
    with col1:
        nan_count = df['congestion'].isna().sum()
        nan_ratio = (nan_count / len(df)) * 100
        st.metric(
            "결측값 (NaN)",
            f"{nan_count:,}건",
            delta=f"{nan_ratio:.2f}%",
            delta_color="inverse"
        )
    
    # 0값 분석
    with col2:
        zero_count = (df['congestion'] == 0).sum()
        zero_ratio = (zero_count / len(df)) * 100
        st.metric(
            "0값 데이터",
            f"{zero_count:,}건",
            delta=f"{zero_ratio:.2f}%",
            delta_color="inverse"
        )
    
    # 이상치 (150% 이상)
    with col3:
        outlier_150 = (df['congestion'] >= 150).sum()
        outlier_150_ratio = (outlier_150 / len(df)) * 100
        st.metric(
            "고혼잡 (150%+)",
            f"{outlier_150:,}건",
            delta=f"{outlier_150_ratio:.2f}%"
        )
    
    # 이상치 (200% 이상)
    with col4:
        outlier_200 = (df['congestion'] >= 200).sum()
        outlier_200_ratio = (outlier_200 / len(df)) * 100
        st.metric(
            "극단값 (200%+)",
            f"{outlier_200:,}건",
            delta=f"{outlier_200_ratio:.2f}%",
            delta_color="inverse"
        )
    
    # 품질 상태 표시
    quality_score = 100 - nan_ratio - (zero_ratio * 0.5) - (outlier_200_ratio * 2)
    quality_score = max(0, min(100, quality_score))
    
    if quality_score >= 90:
        st.success(f"✅ 데이터 품질 양호 (점수: {quality_score:.1f}/100)")
    elif quality_score >= 70:
        st.warning(f"⚠️ 데이터 품질 주의 (점수: {quality_score:.1f}/100)")
    else:
        st.error(f"❌ 데이터 품질 점검 필요 (점수: {quality_score:.1f}/100)")
    
    st.markdown("---")
    
    # 이상치 탐지
    st.subheader("🔍 이상치 탐지")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        threshold = st.slider(
            "이상치 임계값 (%)",
            min_value=100,
            max_value=200,
            value=150,
            step=10,
            help="이 값 이상의 혼잡도를 이상치로 간주합니다."
        )
    
    # 이상치 데이터
    df_outliers = df[df['congestion'] >= threshold].copy()
    df_outliers = df_outliers.sort_values('congestion', ascending=False)
    
    with col2:
        st.metric(
            f"임계값 {threshold}% 이상 데이터",
            f"{len(df_outliers):,}건",
            delta=f"전체의 {(len(df_outliers)/len(df)*100):.2f}%"
        )
    
    if len(df_outliers) > 0:
        # 이상치 테이블
        display_outliers = df_outliers[['line', 'station', 'direction', 'time_slot', 'congestion']].copy()
        display_outliers.columns = ['호선', '역명', '방향', '시간대', '혼잡도(%)']
        display_outliers['혼잡도(%)'] = display_outliers['혼잡도(%)'].round(1)
        
        st.dataframe(
            display_outliers.head(50),
            use_container_width=True,
            hide_index=True,
            height=300
        )
        
        if len(df_outliers) > 50:
            st.caption(f"상위 50건만 표시 (전체 {len(df_outliers):,}건)")
        
        # 다운로드
        create_download_button(
            display_outliers,
            f"이상치_데이터_{threshold}이상.csv",
            "📥 이상치 데이터 다운로드"
        )
    else:
        st.success(f"임계값 {threshold}% 이상의 데이터가 없습니다.")
    
    st.markdown("---")
    
    # 혼잡도 분포
    st.subheader("📈 혼잡도 분포")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 히스토그램
        fig_hist = px.histogram(
            df,
            x='congestion',
            nbins=50,
            labels={'congestion': '혼잡도 (%)', 'count': '빈도'},
            title="혼잡도 분포 (히스토그램)"
        )
        
        # 기준선 추가
        fig_hist.add_vline(x=30, line_dash="dash", line_color="green", annotation_text="여유(30%)")
        fig_hist.add_vline(x=70, line_dash="dash", line_color="orange", annotation_text="보통(70%)")
        fig_hist.add_vline(x=130, line_dash="dash", line_color="red", annotation_text="혼잡(130%)")
        
        fig_hist.update_layout(height=400)
        
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # 기술 통계
        st.markdown("#### 기술 통계")
        
        stats = {
            '평균': df['congestion'].mean(),
            '중앙값': df['congestion'].median(),
            '표준편차': df['congestion'].std(),
            '최소값': df['congestion'].min(),
            '최대값': df['congestion'].max(),
            '25% 분위': df['congestion'].quantile(0.25),
            '75% 분위': df['congestion'].quantile(0.75)
        }
        
        for name, value in stats.items():
            st.metric(name, f"{value:.1f}%")
    
    st.markdown("---")
    
    # 혼잡도 구간별 분포
    st.subheader("📊 혼잡도 구간별 분포")
    
    # 구간 정의
    bins = [0, 30, 70, 130, float('inf')]
    labels = ['여유(0-30%)', '보통(30-70%)', '혼잡(70-130%)', '매우혼잡(130%+)']
    
    df['congestion_level'] = pd.cut(
        df['congestion'],
        bins=bins,
        labels=labels,
        include_lowest=True
    )
    
    level_counts = df['congestion_level'].value_counts().sort_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 파이 차트
        fig_pie = px.pie(
            values=level_counts.values,
            names=level_counts.index,
            title="혼잡도 구간 비율",
            color_discrete_sequence=['#4CAF50', '#FFC107', '#FF9800', '#F44336']
        )
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # 테이블
        level_df = pd.DataFrame({
            '구간': level_counts.index,
            '건수': level_counts.values,
            '비율(%)': (level_counts.values / len(df) * 100).round(2)
        })
        st.dataframe(level_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # 호선별 데이터 현황
    st.subheader("📋 호선별 데이터 현황")
    
    line_stats = df.groupby('line').agg({
        'station': 'nunique',
        'congestion': ['count', 'mean', 'max']
    }).reset_index()
    
    line_stats.columns = ['호선', '역 수', '데이터 건수', '평균 혼잡도(%)', '최대 혼잡도(%)']
    line_stats['평균 혼잡도(%)'] = line_stats['평균 혼잡도(%)'].round(1)
    line_stats['최대 혼잡도(%)'] = line_stats['최대 혼잡도(%)'].round(1)
    
    # 호선 정렬
    line_stats['sort_key'] = line_stats['호선'].apply(
        lambda x: int(x.replace('호선', '')) if '호선' in x else 999
    )
    line_stats = line_stats.sort_values('sort_key').drop('sort_key', axis=1)
    
    # 결측/0값 비율 계산
    line_quality = []
    for line in line_stats['호선']:
        line_data = df[df['line'] == line]
        nan_ratio = (line_data['congestion'].isna().sum() / len(line_data)) * 100
        zero_ratio = ((line_data['congestion'] == 0).sum() / len(line_data)) * 100
        line_quality.append({
            '호선': line,
            '결측비율(%)': round(nan_ratio, 2),
            '0값비율(%)': round(zero_ratio, 2)
        })
    
    quality_df = pd.DataFrame(line_quality)
    line_stats = line_stats.merge(quality_df, on='호선')
    
    st.dataframe(
        line_stats,
        use_container_width=True,
        hide_index=True
    )
    
    # 호선별 평균 혼잡도 차트
    fig_line_avg = px.bar(
        line_stats,
        x='호선',
        y='평균 혼잡도(%)',
        color='평균 혼잡도(%)',
        color_continuous_scale='Reds',
        title="호선별 평균 혼잡도"
    )
    fig_line_avg.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_line_avg, use_container_width=True)
    
    st.markdown("---")
    
    # 시간대별 데이터 현황
    st.subheader("⏰ 시간대별 데이터 현황")
    
    time_stats = df.groupby('time_slot').agg({
        'congestion': ['count', 'mean', 'max']
    }).reset_index()
    time_stats.columns = ['시간대', '데이터 건수', '평균 혼잡도(%)', '최대 혼잡도(%)']
    time_stats['평균 혼잡도(%)'] = time_stats['평균 혼잡도(%)'].round(1)
    time_stats['최대 혼잡도(%)'] = time_stats['최대 혼잡도(%)'].round(1)
    
    # 시간대별 평균 혼잡도 차트
    fig_time = px.line(
        time_stats,
        x='시간대',
        y='평균 혼잡도(%)',
        markers=True,
        title="시간대별 평균 혼잡도"
    )
    fig_time.update_layout(height=350, xaxis={'type': 'category'})
    st.plotly_chart(fig_time, use_container_width=True)
    
    st.markdown("---")
    
    # 다운로드 섹션
    st.subheader("📥 데이터 다운로드")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 전체 데이터
        download_full = df[['line', 'station', 'direction', 'time_slot', 'congestion']].copy()
        download_full.columns = ['호선', '역명', '방향', '시간대', '혼잡도(%)']
        create_download_button(
            download_full,
            "전체_혼잡도_데이터.csv",
            "📥 전체 데이터 다운로드"
        )
    
    with col2:
        # 호선별 통계
        create_download_button(
            line_stats,
            "호선별_통계.csv",
            "📥 호선별 통계 다운로드"
        )
    
    with col3:
        # 시간대별 통계
        create_download_button(
            time_stats,
            "시간대별_통계.csv",
            "📥 시간대별 통계 다운로드"
        )
    
    # 데이터 설명
    st.markdown("---")
    with st.expander("💡 혼잡도 데이터 해석 가이드"):
        st.markdown("""
        ### 혼잡도란?
        - 혼잡도는 **열차 정원 대비 승객 수의 비율**을 나타냅니다.
        - 100%는 모든 좌석이 차고 일부 승객이 서 있는 상태입니다.
        
        ### 혼잡도 기준
        | 구간 | 혼잡도 | 상태 |
        |------|--------|------|
        | 🟢 여유 | 0-30% | 좌석에 여유 있음 |
        | 🟡 보통 | 30-70% | 좌석 대부분 차 있음 |
        | 🟠 혼잡 | 70-130% | 서 있는 승객 많음 |
        | 🔴 매우혼잡 | 130%+ | 승하차 어려움 |
        
        ### 데이터 품질 참고사항
        - **0값**: 운행하지 않거나 데이터 수집 누락 가능성
        - **150% 이상**: 출퇴근 러시아워에 일부 역에서 발생 가능
        - **200% 이상**: 매우 드문 경우로 데이터 오류 가능성 확인 필요
        
        ### 데이터 출처
        - 서울교통공사 지하철 혼잡도 정보 (2025년 9월 30일 기준)
        """)


if __name__ == "__main__":
    main()

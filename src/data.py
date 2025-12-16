"""
데이터 로딩 및 전처리 모듈
"""
import pandas as pd
import streamlit as st
from pathlib import Path
from typing import Optional

# 시간대 순서 정의 (05:30 ~ 00:30)
TIME_ORDER = [
    '05:30', '06:00', '06:30', '07:00', '07:30', '08:00', '08:30', '09:00', '09:30',
    '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00',
    '14:30', '15:00', '15:30', '16:00', '16:30', '17:00', '17:30', '18:00', '18:30',
    '19:00', '19:30', '20:00', '20:30', '21:00', '21:30', '22:00', '22:30', '23:00',
    '23:30', '00:00', '00:30'
]


def load_raw_data(csv_path: str = "서울교통공사_지하철혼잡도정보_20250930.csv") -> pd.DataFrame:
    """
    CSV 파일을 로드합니다.
    
    Args:
        csv_path: CSV 파일 경로
        
    Returns:
        pd.DataFrame: 로드된 데이터프레임
    """
    # 인코딩 시도 순서
    encodings = ['cp949', 'euc-kr', 'utf-8-sig', 'utf-8']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            st.error(f"파일 로딩 중 오류 발생: {e}")
            raise
    
    raise ValueError(f"지원되는 인코딩으로 파일을 읽을 수 없습니다: {csv_path}")


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    데이터를 정제합니다.
    
    Args:
        df: 원본 데이터프레임
        
    Returns:
        pd.DataFrame: 정제된 데이터프레임
    """
    df = df.copy()
    
    # 컬럼명 정리 (좌우 공백 제거)
    df.columns = df.columns.str.strip()
    
    # 문자열 컬럼 정리
    for col in ['요일구분', '호선', '출발역', '상하구분']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    
    # 역번호를 숫자로 변환
    if '역번호' in df.columns:
        df['역번호'] = pd.to_numeric(df['역번호'], errors='coerce')
    
    return df


def melt_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Wide 포맷을 Long 포맷으로 변환합니다.
    
    Args:
        df: Wide 포맷 데이터프레임
        
    Returns:
        pd.DataFrame: Long 포맷 데이터프레임
    """
    # 시간대 컬럼 식별 (시, 분이 포함된 컬럼)
    time_cols = [col for col in df.columns if '시' in col and '분' in col]
    
    # 기본 컬럼
    id_cols = ['요일구분', '호선', '역번호', '출발역', '상하구분']
    
    # Melt 수행
    df_long = df.melt(
        id_vars=id_cols,
        value_vars=time_cols,
        var_name='time_slot',
        value_name='congestion'
    )
    
    # 시간대 포맷 변환 (예: "5시30분" -> "05:30")
    df_long['time_slot'] = df_long['time_slot'].apply(format_time_column)
    
    # 혼잡도를 숫자로 변환
    df_long['congestion'] = pd.to_numeric(df_long['congestion'], errors='coerce')
    
    # 컬럼명 영문화
    df_long = df_long.rename(columns={
        '요일구분': 'day_type',
        '호선': 'line',
        '역번호': 'station_id',
        '출발역': 'station',
        '상하구분': 'direction'
    })
    
    # NaN 제거
    df_long = df_long.dropna(subset=['congestion'])
    
    # 시간대 순서 적용을 위한 categorical 변환
    df_long['time_slot'] = pd.Categorical(
        df_long['time_slot'],
        categories=TIME_ORDER,
        ordered=True
    )
    
    # 정렬
    df_long = df_long.sort_values(['line', 'station', 'direction', 'time_slot'])
    
    return df_long.reset_index(drop=True)


def format_time_column(time_str: str) -> str:
    """
    시간 컬럼명을 표준 포맷으로 변환합니다.
    
    Args:
        time_str: 원본 시간 문자열 (예: "5시30분", "08시00분")
        
    Returns:
        str: 포맷된 시간 문자열 (예: "05:30", "08:00")
    """
    import re
    
    # "시"와 "분" 제거하고 숫자만 추출
    match = re.search(r'(\d+)시(\d+)분', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return f"{hour:02d}:{minute:02d}"
    
    return time_str


@st.cache_data
def get_data(csv_path: str = "서울교통공사_지하철혼잡도정보_20250930.csv") -> pd.DataFrame:
    """
    데이터를 로드하고 전처리한 결과를 캐시하여 반환합니다.
    
    Args:
        csv_path: CSV 파일 경로
        
    Returns:
        pd.DataFrame: 전처리된 Long 포맷 데이터프레임
    """
    # 파일 경로 확인
    file_path = Path(csv_path)
    if not file_path.exists():
        st.error(f"파일을 찾을 수 없습니다: {csv_path}")
        st.info("현재 작업 디렉토리에 CSV 파일이 있는지 확인해주세요.")
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {csv_path}")
    
    # 데이터 로딩 및 전처리 파이프라인
    df_raw = load_raw_data(csv_path)
    df_clean = clean_data(df_raw)
    df_long = melt_to_long(df_clean)
    
    return df_long


def get_unique_values(df: pd.DataFrame, column: str) -> list:
    """
    특정 컬럼의 고유값을 정렬하여 반환합니다.
    
    Args:
        df: 데이터프레임
        column: 컬럼명
        
    Returns:
        list: 정렬된 고유값 리스트
    """
    if column not in df.columns:
        return []
    
    unique_vals = df[column].dropna().unique()
    
    # 호선의 경우 숫자 기준 정렬
    if column == 'line':
        return sorted(unique_vals, key=lambda x: int(x.replace('호선', '')) if '호선' in x else 999)
    
    return sorted(unique_vals)


def get_stations_by_line(df: pd.DataFrame, line: Optional[str] = None) -> list:
    """
    특정 호선의 역 목록을 반환합니다.
    
    Args:
        df: 데이터프레임
        line: 호선명 (None이면 전체)
        
    Returns:
        list: 역명 리스트
    """
    if line:
        df_filtered = df[df['line'] == line]
    else:
        df_filtered = df
    
    stations = df_filtered['station'].dropna().unique()
    return sorted(stations)

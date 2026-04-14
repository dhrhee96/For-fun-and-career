# data_scraper.py
import pandas as pd
import FinanceDataReader as fdr

def get_krx_kospi200_options(target_date=None):
    """
    KRX 서버 대신, 직접 다운로드 받은 로컬 CSV 파일을 읽어옵니다.
    """
    try:
        # KRX에서 받은 CSV는 기본적으로 'euc-kr' 또는 'cp949' 인코딩입니다.
        df = pd.read_csv('data_0020_20260414.csv', encoding='cp949')
        return df
    except FileNotFoundError:
        print("❌ [오류] data_0020_20260414.csv 파일을 찾을 수 없습니다. 같은 폴더에 있는지 확인해주세요.")
        return None
    except Exception as e:
        print(f"❌ [오류] 파일을 읽는 중 문제 발생: {e}")
        return None

def get_risk_free_rate(start_date, end_date):
    """국고채 3년물 금리 수집 (FDR 라이브러리는 정상 작동하므로 그대로 둡니다)"""
    df_bond = fdr.DataReader('KR3YT=RR', start_date, end_date)
    return df_bond
# main.py
import numpy as np
import pandas as pd
from data_scraper import get_krx_kospi200_options
from pricing_engine import implied_volatility_call, bs_greeks_call
from visualizer import plot_volatility_surface

def run_quant_system():
    print("1. KRX 시장 데이터 스크래핑 시작...")
    # 타겟 일자 설정 (최근 평일 날짜로 설정해야 데이터가 나옵니다)
    target_date = '20240412' 
    
    try:
        # 데이터 수집
        df_options = get_krx_kospi200_options(target_date)
        print("데이터 스크래핑 성공! 총 데이터 수:", len(df_options))
        
        # 콜옵션 데이터만 필터링하고 필요한 컬럼 추출 ('종목명' 등에 콜/풋 정보가 있음)
        # KRX 실제 데이터 포맷에 맞게 전처리가 필요합니다.
        # (이 부분은 KRX csv 파일 구조에 따라 Pandas로 정제하는 로직이 들어갑니다)
        
        # -------------------------------------------------------------
        # [예시] 스크래핑한 데이터 중 특정 콜옵션 1개의 그릭스를 확인해보는 로직
        S0_market = 365.20   # 당일 코스피200 종가 가정
        K_target = 370.0     # 행사가 370 짜리 콜옵션
        T_target = 30 / 365  # 만기 30일 남음
        r_current = 0.035    # 국채 금리 3.5%
        market_price = 4.50  # 시장에서 거래되는 옵션 가격(pt)
        
        print("\n2. 내재변동성 역산 및 그릭스 산출...")
        iv = implied_volatility_call(market_price, S0_market, K_target, T_target, r_current)
        greeks = bs_greeks_call(S0_market, K_target, T_target, r_current, iv)
        
        print(f"시장 가격: {market_price} pt")
        print(f"역산된 IV: {iv*100:.2f}%")
        print(f"Delta (델타): {greeks['Delta']:.4f}")
        print(f"Gamma (감마): {greeks['Gamma']:.4f}")
        print(f"Theta (세타): {greeks['Theta']:.4f}")
        print(f"Vega (베가) : {greeks['Vega']:.4f}")
        
        # -------------------------------------------------------------
        # 3. 전체 데이터를 배열로 만들어 plot_volatility_surface(K, T, IV) 호출
        # print("\n3. 변동성 곡면 렌더링...")
        # plot_volatility_surface(K_grid, T_grid, IV_grid)
        
    except Exception as e:
        print("에러 발생:", e)

if __name__ == "__main__":
    run_quant_system()
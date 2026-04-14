# pricing_engine.py
import numpy as np
import scipy.linalg as linalg
from scipy.stats import norm

# [1] 기본 블랙-숄즈 콜옵션 가격 계산기
def bs_call(S, K, T, r, sigma):
    # 잔존만기가 0이거나 음수면 내재가치만 반환 (만기 도래)
    if T <= 0: return max(S - K, 0)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

# [2] 그릭스 (Greeks) 산출기 - 리스크 관리의 핵심
def bs_greeks_call(S, K, T, r, sigma):
    """
    콜옵션의 5대 그릭스를 계산하여 딕셔너리로 반환합니다.
    """
    if T <= 0: return {'Delta': 0, 'Gamma': 0, 'Theta': 0, 'Vega': 0, 'Rho': 0}
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # 1. 델타 (Delta): 기초자산(KOSPI200)이 1pt 변할 때 옵션 가격의 변화량
    delta = norm.cdf(d1)
    
    # 2. 감마 (Gamma): 기초자산 변동에 따른 델타의 변화량 (델타의 가속도)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    # 3. 세타 (Theta): 시간이 하루(1년=1.0 기준) 지날 때 깎이는 옵션의 가치 (시간 가치 감소)
    theta = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)
    
    # 4. 베가 (Vega): 변동성이 1% (0.01) 상승할 때 옵션 가격의 상승량
    vega = S * np.sqrt(T) * norm.pdf(d1)
    
    # 5. 로 (Rho): 금리가 1% 상승할 때 옵션 가격의 변화량
    rho = K * T * np.exp(-r * T) * norm.cdf(d2)
    
    return {'Delta': delta, 'Gamma': gamma, 'Theta': theta, 'Vega': vega, 'Rho': rho}

# [3] 내재변동성 (IV) 역산기 (뉴턴-랩슨)
def implied_volatility_call(market_price, S, K, T, r, tol=1e-5, max_iter=100):
    sigma = 0.20 # 초기 추정치 20%
    for _ in range(max_iter):
        price_diff = bs_call(S, K, T, r, sigma) - market_price
        if abs(price_diff) < tol: return sigma
        vega = bs_greeks_call(S, K, T, r, sigma)['Vega']
        if vega < 1e-8: break # 베가가 0에 수렴하면 발산 방지
        sigma -= price_diff / vega
    return sigma

# [4] 정밀 수치해석기 (크랭크-니콜슨 FDM)
def fdm_crank_nicolson_call(S0, K, T, r, sigma, M=400, N=400):
    # (앞서 작성했던 크랭크-니콜슨 FDM 코드를 여기에 그대로 위치시킵니다.)
    pass # 지면상 내용 생략 (위의 FDM 코드와 동일)
# visualizer.py
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.ticker import FuncFormatter
import platform

def plot_volatility_surface(K_grid, T_grid, IV_grid):
    """
    행사가(K), 잔존만기(T), 내재변동성(IV) 2D 배열을 받아 3D 곡면을 렌더링
    """
    if platform.system() == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif platform.system() == 'Darwin':
        plt.rc('font', family='AppleGothic')
    plt.rcParams['axes.unicode_minus'] = False

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')

    surf = ax.plot_surface(K_grid, T_grid, IV_grid, cmap='plasma', 
                           edgecolor='k', linewidth=0.1, alpha=0.9)

    ax.set_title('KOSPI 200 변동성 곡면 (실제 KRX 데이터 연동)', fontsize=16, fontweight='bold')
    ax.set_xlabel('행사가격 (Strike, pt)', fontsize=12)
    ax.set_ylabel('잔존만기 (Maturity, Years)', fontsize=12)
    ax.set_zlabel('내재변동성 (IV, %)', fontsize=12)

    ax.zaxis.set_major_formatter(FuncFormatter(lambda z, _: f'{z*100:.1f}%'))
    
    cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
    cbar.set_label('내재변동성', rotation=270, labelpad=20)
    cbar.formatter = FuncFormatter(lambda z, _: f'{z*100:.1f}%')
    cbar.update_ticks()

    ax.view_init(elev=25, azim=-120)
    plt.show()
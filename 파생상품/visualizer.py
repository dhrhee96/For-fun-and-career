# visualizer.py
import platform

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


def _set_korean_font() -> None:
    """운영체제별 한글 폰트를 설정합니다."""
    if platform.system() == "Windows":
        plt.rc("font", family="Malgun Gothic")
    elif platform.system() == "Darwin":
        plt.rc("font", family="AppleGothic")
    plt.rcParams["axes.unicode_minus"] = False


def plot_volatility_surface(K_grid, T_grid, IV_grid):
    """
    행사가(K), 잔존만기(T), 내재변동성(IV) 배열을 받아 3D 곡면을 렌더링합니다.

    데이터가 충분하지 않아 정규 격자가 아니라면 thin surface보다는
    산점도에 가까운 형태로 보일 수 있습니다. 이 경우 별도 보간 로직을 추가하면 됩니다.
    """
    _set_korean_font()

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection="3d")

    surf = ax.plot_surface(
        K_grid,
        T_grid,
        IV_grid,
        cmap="plasma",
        edgecolor="k",
        linewidth=0.1,
        alpha=0.9,
    )

    ax.set_title("KOSPI 200 Implied Volatility Surface", fontsize=16, fontweight="bold")
    ax.set_xlabel("Strike (pt)", fontsize=12)
    ax.set_ylabel("Maturity (years)", fontsize=12)
    ax.set_zlabel("Implied Volatility", fontsize=12)

    ax.zaxis.set_major_formatter(FuncFormatter(lambda z, _: f"{z * 100:.1f}%"))

    cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
    cbar.set_label("Implied Volatility", rotation=270, labelpad=20)
    cbar.formatter = FuncFormatter(lambda z, _: f"{z * 100:.1f}%")
    cbar.update_ticks()

    ax.view_init(elev=25, azim=-120)
    plt.tight_layout()
    plt.show()

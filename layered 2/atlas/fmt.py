"""Display formats shared by tools and the harness."""


def money(v: float) -> str:
    a = abs(v)
    if a >= 1e9:
        return f"${a / 1e9:.2f}B"
    if a >= 1e6:
        return f"${a / 1e6:.1f}M"
    if a >= 1e3:
        return f"${round(a / 1e3):.0f}K"
    return f"${round(a):.0f}"


def pct(v: float, d: int = 1) -> str:
    return f"{v * 100:.{d}f}%"

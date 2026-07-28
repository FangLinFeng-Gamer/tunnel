from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt


def box_plot_outlier_bounds(
    values: npt.ArrayLike,
    *,
    box_scale: float,
    nonzero: bool,
) -> tuple[float, float]:
    """按箱线图 IQR 规则计算异常值上下界。"""

    array = np.asarray(values, dtype=np.float64)
    candidates = array[array != 0] if nonzero else array
    if candidates.size == 0:
        candidates = array
    if candidates.size == 0:
        return -math.inf, math.inf

    q1, q3 = np.quantile(candidates, [0.25, 0.75])
    iqr = float(q3 - q1)
    return (
        float(q1 - box_scale * iqr),
        float(q3 + box_scale * iqr),
    )

"""H41-I: exact nearest-strand local strike; no labels or old predictions as inputs."""
import numpy as np
import shapely
from shapely.strtree import STRtree
from model import axial_delta


def nearest_local_strikes(lines, xy, half_window_m=250.0):
    """Axial tangent at the exact nearest point, ties resolved by source order.

    A hairpin can have a zero chord even with nonzero arclength: return NaN so
    callers suppress confidence, rather than invent a north-facing tangent.
    """
    xy = np.asarray(xy, dtype=float).reshape(-1, 2)
    result = np.full(len(xy), np.nan, dtype=np.float32)
    if half_window_m <= 0:
        raise ValueError('half_window_m must be positive')
    if not lines or not len(xy):
        return result
    geometries = np.asarray(lines, dtype=object)
    tree = STRtree(geometries)
    for start in range(0, len(xy), 20000):
        pts = shapely.points(xy[start:start + 20000])
        matches = tree.query_nearest(pts, all_matches=True)
        # GEOS traversal order is not a stable tie breaker.
        order = np.lexsort((matches[1], matches[0]))
        sorted_matches = matches[:, order]
        first = np.r_[True, np.diff(sorted_matches[0]) != 0]
        source = sorted_matches[1, first]
        selected = geometries[source]
        distance = shapely.line_locate_point(selected, pts)
        before = shapely.line_interpolate_point(selected, np.maximum(distance - half_window_m, 0))
        after = shapely.line_interpolate_point(selected, np.minimum(distance + half_window_m, shapely.length(selected)))
        dx = shapely.get_x(after) - shapely.get_x(before)
        dy = shapely.get_y(after) - shapely.get_y(before)
        strike = np.mod(np.degrees(np.arctan2(dx, dy)), 180)
        strike[np.hypot(dx, dy) <= 1e-8] = np.nan
        result[start:start + len(pts)] = strike
    return result


def local_prediction(records, corridor, distances, orientation, detected, transform):
    """The closer population is defined identically to H41-A (ties -> N/NNE)."""
    if transform.b or transform.d or transform.a <= 0 or transform.e >= 0:
        raise ValueError('Expected north-up metric grid')
    candidate = np.zeros(corridor.shape, dtype=np.float32)
    rr, cc = np.nonzero((corridor > 0) & detected)
    families = np.where(distances[0][rr, cc] < distances[1][rr, cc], 0, 1)
    stats = {'queried_pixels': len(rr), 'undefined_tangents': 0, 'family_pixels': {}}
    for family in (0, 1):
        idx = families == family
        r, c = rr[idx], cc[idx]
        xy = np.column_stack((transform.c + (c + .5) * transform.a,
                              transform.f + (r + .5) * transform.e))
        strike = nearest_local_strikes([rec['geometry'] for rec in records if rec['family'] == family], xy)
        ok = np.isfinite(strike)
        stats['undefined_tangents'] += int((~ok).sum())
        stats['family_pixels'][str(family)] = int(ok.sum())
        r, c, strike = r[ok], c[ok], strike[ok]
        match = np.cos(np.radians(axial_delta(orientation[r, c], strike))) ** 8
        candidate[r, c] = np.clip(corridor[r, c] * match, 0, 1)
    return candidate, stats

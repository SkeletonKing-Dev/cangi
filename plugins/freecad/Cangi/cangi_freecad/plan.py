import math

IDLE = {"state": "idle", "text": ""}


def plan(steps):
    """Reduce wire steps to what the HUD draws. Pure function."""
    tool = None
    markers = []
    regions = []
    lines = []
    for s in sorted(steps, key=lambda s: -s.get("priority", 0)):
        p = s.get("payload", {})
        kind = s.get("kind")
        if kind == "highlight" and tool is None and p.get("tool"):
            tool = (p["tool"], bool(p.get("subtle")))
        elif kind == "arrow" and p.get("world"):
            markers.append((tuple(p["world"]), p.get("text", "")))
        elif kind == "region" and p.get("center") and p.get("radius", 0) > 0:
            regions.append({"space": p.get("space", "world"), "center": tuple(p["center"]),
                            "radius": float(p["radius"]), "text": p.get("text", "")})
        elif kind == "panel":
            lines.extend(p.get("lines", []))
    return {"tool": tool, "markers": markers, "regions": regions, "lines": lines}


def circle_points(center, radius, n=48):
    """Closed polyline of n + 1 points around center in the XY plane."""
    cx, cy = center[0], center[1]
    cz = center[2] if len(center) > 2 else 0.0
    return [(cx + radius * math.cos(2 * math.pi * i / n),
             cy + radius * math.sin(2 * math.pi * i / n), cz) for i in range(n + 1)]


def status_text(status):
    state, text = status.get("state", "idle"), status.get("text", "")
    if state == "error":
        return "Error: " + text
    return text

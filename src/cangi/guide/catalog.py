"""Command ids the model may highlight, per platform. Ids outside the catalog are dropped from plans."""
from typing import Dict

FREECAD: Dict[str, str] = {
    "Std_New": "create a new document",
    "Std_ViewFitAll": "fit all objects in the view",
    "Std_ViewIsometric": "isometric view",
    "PartDesign_Body": "create a Body",
    "PartDesign_Pad": "extrude a sketch (Pad)",
    "PartDesign_Pocket": "cut with a sketch (Pocket)",
    "PartDesign_Fillet": "round edges",
    "PartDesign_Chamfer": "chamfer edges",
    "Sketcher_NewSketch": "create a new sketch",
    "Sketcher_LeaveSketch": "close the sketch",
    "Sketcher_CreateLine": "draw a line",
    "Sketcher_CreateRectangle": "draw a rectangle",
    "Sketcher_CreateCircle": "draw a circle",
    "Sketcher_ConstrainCoincidentUnified": "coincident constraint",
    "Sketcher_ConstrainHorizontal": "horizontal constraint",
    "Sketcher_ConstrainVertical": "vertical constraint",
    "Sketcher_ConstrainEqual": "equal length constraint",
    "Sketcher_ConstrainLock": "lock position",
    "Sketcher_ConstrainDistanceX": "horizontal distance",
    "Sketcher_ConstrainDistanceY": "vertical distance",
    "Sketcher_Dimension": "dimension (distance, radius, angle)",
    "Part_Box": "create a box primitive",
    "Part_Cylinder": "create a cylinder primitive",
    "Part_Sphere": "create a sphere primitive",
}

APP_NAMES = {"freecad": "FreeCAD 1.x", "autocad": "AutoCAD", "qcad": "QCAD"}
CATALOGS: Dict[str, Dict[str, str]] = {"freecad": FREECAD}

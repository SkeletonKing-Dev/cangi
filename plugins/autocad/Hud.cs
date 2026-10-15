using System;
using System.Collections.Generic;
using System.Text.Json;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.GraphicsInterface;
using Autodesk.AutoCAD.Windows;
using AcApp = Autodesk.AutoCAD.ApplicationServices.Application;

namespace Cangi
{
    // Overlay built on AutoCAD facilities: transient graphics in the drawing, a palette for text.
    // Must be used from the UI thread.
    public class Hud
    {
        readonly List<Entity> transients = new List<Entity>();
        readonly PaletteSet palette;
        readonly System.Windows.Forms.Label label;

        public Hud()
        {
            label = new System.Windows.Forms.Label
            {
                Dock = System.Windows.Forms.DockStyle.Fill,
                Padding = new System.Windows.Forms.Padding(8),
            };
            palette = new PaletteSet("Cangi");
            palette.Add("Cangi", label);
        }

        public void Apply(JsonElement frame)
        {
            Clear();
            var lines = new List<string>();
            var steps = new List<JsonElement>();
            if (frame.TryGetProperty("steps", out var arr))
                foreach (var s in arr.EnumerateArray()) steps.Add(s);
            steps.Sort((a, b) => b.GetProperty("priority").GetInt32().CompareTo(a.GetProperty("priority").GetInt32()));

            foreach (var s in steps)
            {
                var p = s.GetProperty("payload");
                switch (s.GetProperty("kind").GetString())
                {
                    case "highlight":
                        if (p.TryGetProperty("tool", out var tool)) lines.Add("Next tool: " + tool.GetString());
                        break;
                    case "arrow":
                        var w = p.GetProperty("world");
                        string text = p.TryGetProperty("text", out var t) ? t.GetString() : "";
                        AddMarker(new Point3d(w[0].GetDouble(), w[1].GetDouble(), w[2].GetDouble()), text);
                        if (text.Length > 0) lines.Add(text);
                        break;
                    case "panel":
                        foreach (var l in p.GetProperty("lines").EnumerateArray()) lines.Add(l.GetString());
                        break;
                }
            }
            label.Text = string.Join("\n", lines);
            palette.Visible = lines.Count > 0;
        }

        public void Clear()
        {
            var tm = TransientManager.CurrentTransientManager;
            foreach (var e in transients)
            {
                tm.EraseTransient(e, new IntegerCollection());
                e.Dispose();
            }
            transients.Clear();
        }

        void AddMarker(Point3d at, string text)
        {
            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return;
            double h;
            using (var view = doc.Editor.GetCurrentView()) h = view.Height;

            var ring = new Circle(at, Vector3d.ZAxis, h * 0.02) { ColorIndex = 1 };
            Add(ring);
            if (text.Length == 0) return;
            var label = new DBText
            {
                Position = at + new Vector3d(h * 0.03, 0, 0),
                Height = h * 0.02,
                TextString = text,
                ColorIndex = 1,
            };
            Add(label);
        }

        void Add(Entity e)
        {
            TransientManager.CurrentTransientManager.AddTransient(
                e, TransientDrawingMode.DirectTopmost, 128, new IntegerCollection());
            transients.Add(e);
        }
    }
}

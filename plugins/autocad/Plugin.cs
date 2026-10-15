using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Runtime;
using AcApp = Autodesk.AutoCAD.ApplicationServices.Application;

[assembly: ExtensionApplication(typeof(Cangi.Plugin))]

namespace Cangi
{
    public class Plugin : IExtensionApplication
    {
        static readonly long EpochTicks = DateTime.UnixEpoch.Ticks;

        readonly HashSet<Document> hookedDocs = new HashSet<Document>();
        readonly Dictionary<Document, Database> hookedDbs = new Dictionary<Document, Database>();
        Link link;
        Hud hud;
        SynchronizationContext ui;

        public void Initialize()
        {
            string host = Environment.GetEnvironmentVariable("CANGI_HOST") ?? "127.0.0.1";
            int port = int.Parse(Environment.GetEnvironmentVariable("CANGI_PORT") ?? "8765");

            ui = SynchronizationContext.Current ?? new System.Windows.Forms.WindowsFormsSynchronizationContext();
            hud = new Hud();
            link = new Link(host, port, OnFrameLine);
            link.Start();

            var dm = AcApp.DocumentManager;
            dm.DocumentCreated += OnDocumentCreated;
            dm.DocumentActivated += OnDocumentActivated;
            dm.DocumentToBeDestroyed += OnDocumentToBeDestroyed;
            foreach (Document d in dm) Hook(d);
        }

        public void Terminate()
        {
            var dm = AcApp.DocumentManager;
            dm.DocumentCreated -= OnDocumentCreated;
            dm.DocumentActivated -= OnDocumentActivated;
            dm.DocumentToBeDestroyed -= OnDocumentToBeDestroyed;
            foreach (var d in new List<Document>(hookedDocs)) Unhook(d);
            link.Dispose();
        }

        void OnFrameLine(string line)
        {
            JsonDocument parsed;
            try { parsed = JsonDocument.Parse(line); }
            catch (JsonException) { return; }
            ui.Post(_ =>
            {
                using (parsed)
                {
                    var root = parsed.RootElement;
                    if (root.TryGetProperty("op", out var op) && op.GetString() == "overlay") hud.Apply(root);
                }
            }, null);
        }

        void OnDocumentCreated(object s, DocumentCollectionEventArgs e) { Emit("DocumentCreated", e.Document.Name, "document"); Hook(e.Document); }
        void OnDocumentActivated(object s, DocumentCollectionEventArgs e) { Emit("DocumentActivated", e.Document.Name, "document"); Hook(e.Document); }
        void OnDocumentToBeDestroyed(object s, DocumentCollectionEventArgs e) { Emit("DocumentToBeDestroyed", e.Document.Name, "document"); Unhook(e.Document); }

        void Hook(Document doc)
        {
            if (doc == null || !hookedDocs.Add(doc)) return;
            doc.CommandWillStart += OnCommandWillStart;
            doc.CommandEnded += OnCommandEnded;
            var db = doc.Database;
            hookedDbs[doc] = db;
            db.ObjectAppended += OnAppended;
            db.ObjectModified += OnModified;
            db.ObjectErased += OnErased;
        }

        void Unhook(Document doc)
        {
            if (!hookedDocs.Remove(doc)) return;
            doc.CommandWillStart -= OnCommandWillStart;
            doc.CommandEnded -= OnCommandEnded;
            if (hookedDbs.TryGetValue(doc, out var db))
            {
                db.ObjectAppended -= OnAppended;
                db.ObjectModified -= OnModified;
                db.ObjectErased -= OnErased;
                hookedDbs.Remove(doc);
            }
        }

        void OnCommandWillStart(object s, CommandEventArgs e) { Emit("CommandWillStart", e.GlobalCommandName, "command", e.GlobalCommandName); }
        void OnCommandEnded(object s, CommandEventArgs e) { Emit("CommandEnded", e.GlobalCommandName, "command", e.GlobalCommandName); }
        void OnAppended(object s, ObjectEventArgs e) { EmitObject("ObjectAppended", e.DBObject); }
        void OnModified(object s, ObjectEventArgs e) { EmitObject("ObjectModified", e.DBObject); }
        void OnErased(object s, ObjectErasedEventArgs e) { EmitObject("ObjectErased", e.DBObject); }

        // Handlers read only the handle and class name. No database access here.
        void EmitObject(string kind, DBObject obj)
        {
            Emit(kind, obj.ObjectId.Handle.ToString(), obj.GetType().Name);
        }

        void Emit(string kind, string id, string type, string cmd = "")
        {
            long ts = (DateTime.UtcNow.Ticks - EpochTicks) * 100L;
            link.Send(JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["platform"] = "autocad",
                ["ts"] = ts,
                ["kind"] = kind,
                ["id"] = id,
                ["type"] = type,
                ["props"] = new Dictionary<string, object>(),
                ["cmd"] = cmd,
            }));
        }
    }
}

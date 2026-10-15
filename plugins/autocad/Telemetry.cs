using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Runtime;

[assembly: ExtensionApplication(typeof(Cangi.Telemetry.Plugin))]

namespace Cangi.Telemetry
{
    public class Plugin : IExtensionApplication
    {
        const string Host = "127.0.0.1";
        const int Port = 8765;

        readonly BlockingCollection<string> outbox = new BlockingCollection<string>(10000);
        readonly HashSet<Database> hookedDbs = new HashSet<Database>();
        readonly HashSet<Document> hookedDocs = new HashSet<Document>();
        Thread sender;

        public void Initialize()
        {
            sender = new Thread(SendLoop) { IsBackground = true, Name = "cangi-sender" };
            sender.Start();

            var dm = Application.DocumentManager;
            dm.DocumentCreated += (s, e) => { Emit("DocumentCreated", e.Document.Name, "document"); Hook(e.Document); };
            dm.DocumentActivated += (s, e) => { Emit("DocumentActivated", e.Document.Name, "document"); Hook(e.Document); };
            dm.DocumentToBeDestroyed += (s, e) => Emit("DocumentToBeDestroyed", e.Document.Name, "document");
            foreach (Document d in dm) Hook(d);
        }

        public void Terminate()
        {
            outbox.CompleteAdding();
        }

        void Hook(Document doc)
        {
            if (doc == null) return;
            if (hookedDocs.Add(doc))
            {
                doc.CommandWillStart += (s, e) => Emit("CommandWillStart", e.GlobalCommandName, "command", e.GlobalCommandName);
                doc.CommandEnded += (s, e) => Emit("CommandEnded", e.GlobalCommandName, "command", e.GlobalCommandName);
            }
            var db = doc.Database;
            if (!hookedDbs.Add(db)) return;
            db.ObjectAppended += (s, e) => EmitObject("ObjectAppended", e.DBObject);
            db.ObjectModified += (s, e) => EmitObject("ObjectModified", e.DBObject);
            db.ObjectErased += (s, e) => EmitObject("ObjectErased", e.DBObject);
        }

        // Handlers read only the handle and class name. No database access here.
        void EmitObject(string kind, DBObject obj)
        {
            Emit(kind, obj.ObjectId.Handle.ToString(), obj.GetType().Name);
        }

        void Emit(string kind, string id, string type, string cmd = "")
        {
            var ts = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() * 1_000_000L;
            var json = JsonSerializer.Serialize(new Dictionary<string, object>
            {
                ["platform"] = "autocad",
                ["ts"] = ts,
                ["kind"] = kind,
                ["id"] = id,
                ["type"] = type,
                ["props"] = new Dictionary<string, object>(),
                ["cmd"] = cmd,
            });
            outbox.TryAdd(json);
        }

        void SendLoop()
        {
            while (!outbox.IsCompleted)
            {
                try
                {
                    using (var client = new TcpClient(Host, Port))
                    using (var w = new StreamWriter(client.GetStream(), new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" })
                    {
                        foreach (var line in outbox.GetConsumingEnumerable())
                            w.WriteLine(line);
                    }
                }
                catch (Exception)
                {
                    Thread.Sleep(1000);
                }
            }
        }
    }
}

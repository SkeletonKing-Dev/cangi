using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace Cangi
{
    // Sends event lines to the hub and passes received frame lines to onFrame (worker thread).
    public class Link : IDisposable
    {
        readonly string host;
        readonly int port;
        readonly Action<string> onFrame;
        readonly BlockingCollection<string> outbox = new BlockingCollection<string>(10000);
        readonly Thread thread;
        volatile bool stop;
        string pending;

        public Link(string host, int port, Action<string> onFrame)
        {
            this.host = host;
            this.port = port;
            this.onFrame = onFrame;
            thread = new Thread(Run) { IsBackground = true, Name = "cangi-link" };
        }

        public void Start() { thread.Start(); }

        public void Send(string json) { outbox.TryAdd(json); }

        public void Dispose()
        {
            stop = true;
            outbox.CompleteAdding();
        }

        void Run()
        {
            while (!stop)
            {
                try { Session(); }
                catch (System.Exception) { }
                if (!stop) Thread.Sleep(1000);
            }
        }

        void Session()
        {
            using (var client = new TcpClient(host, port))
            {
                var stream = client.GetStream();
                bool readerDone = false;
                var reader = new Thread(() =>
                {
                    try
                    {
                        using (var r = new StreamReader(stream, new UTF8Encoding(false), false, 4096, true))
                        {
                            string line;
                            while ((line = r.ReadLine()) != null) onFrame(line);
                        }
                    }
                    catch (System.Exception) { }
                    readerDone = true;
                }) { IsBackground = true, Name = "cangi-link-read" };
                reader.Start();

                using (var w = new StreamWriter(stream, new UTF8Encoding(false), 4096, true) { AutoFlush = true, NewLine = "\n" })
                {
                    while (!stop && !readerDone)
                    {
                        if (pending == null && !outbox.TryTake(out pending, 200)) continue;
                        w.WriteLine(pending);
                        pending = null;
                    }
                }
            }
        }
    }
}

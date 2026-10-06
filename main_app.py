import os
import sys
import json
import threading
import time
import socket
import http.server
import socketserver
import webview

def get_exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

EXE_DIR = get_exe_dir()
DATA_DIR = os.path.join(EXE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_FILE = os.path.join(DATA_DIR, 'sibos_db.json')

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

class Api:
    def save_db(self, key, value):
        try:
            db = {}
            if os.path.exists(DB_FILE):
                try:
                    with open(DB_FILE, 'r', encoding='utf-8') as f:
                        db = json.load(f)
                except Exception:
                    db = {}
            if value is None:
                db.pop(key, None)
            else:
                db[key] = value
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print("save_db error:", e)
            return False

    def load_db(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

class SiBosHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        # Intercept index.html to inject saved data from sibos_db.json
        clean_path = self.path.split('?')[0]
        if clean_path in ('', '/', '/index.html'):
            index_path = os.path.join(get_base_dir(), 'index.html')
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    html = f.read()
                
                db_json_str = "{}"
                if os.path.exists(DB_FILE):
                    try:
                        with open(DB_FILE, 'r', encoding='utf-8') as f:
                            raw_data = f.read().strip()
                            if raw_data:
                                db_json_str = raw_data
                    except Exception as e:
                        print("Error reading DB_FILE:", e)

                sync_script = f"""<script>
(function() {{
  try {{
    var db = {db_json_str};
    if (db && typeof db === 'object') {{
      for (var k in db) {{
        if (db[k] !== null && db[k] !== undefined) {{
          var val = typeof db[k] === 'string' ? db[k] : JSON.stringify(db[k]);
          localStorage.setItem(k, val);
        }}
      }}
    }}
  }} catch(e) {{ console.error("DB init sync error:", e); }}
}})();
</script>"""
                if '<head>' in html:
                    html = html.replace('<head>', '<head>\n' + sync_script, 1)
                else:
                    html = sync_script + html

                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
                return

        return super().do_GET()

def start_server(port, directory):
    os.chdir(directory)
    handler = SiBosHTTPRequestHandler
    with socketserver.TCPServer(('127.0.0.1', port), handler) as httpd:
        httpd.serve_forever()

if __name__ == '__main__':
    base_dir = get_base_dir()
    
    port = 5173
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', port))
        s.close()
    except Exception:
        port = find_free_port()

    server_thread = threading.Thread(target=start_server, args=(port, base_dir), daemon=True)
    server_thread.start()

    time.sleep(0.5)

    icon_path = os.path.join(base_dir, 'sibos_icon.ico')
    url = f'http://127.0.0.1:{port}/index.html'

    api = Api()
    webview_storage = os.path.join(DATA_DIR, 'webview_profile')
    os.makedirs(webview_storage, exist_ok=True)

    window = webview.create_window(
        title='SiBOS — Aplikasi Pengelolaan Dana BOS & Standing Instruction',
        url=url,
        js_api=api,
        width=1280,
        height=820,
        min_size=(900, 600),
        resizable=True
    )

    webview.start(
        storage_path=webview_storage,
        icon=icon_path if os.path.exists(icon_path) else None
    )

import os
import json
import subprocess
import platform
import psutil
import threading
from flask import Flask, render_template, jsonify, request, abort
from flask_socketio import SocketIO, emit
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'spiderpi_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configurações
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

def get_system_stats():
    """Retorna estatísticas do sistema."""
    stats = {
        "cpu_usage": psutil.cpu_percent(interval=None),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "temp": "N/A"
    }
    
    # Tenta obter temperatura no Raspberry Pi
    try:
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read()) / 1000.0
                stats["temp"] = f"{temp:.1f}°C"
    except:
        pass
        
    return stats

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    return jsonify(get_system_stats())

@app.route('/api/logs')
def list_logs():
    logs = []
    for file in sorted(LOG_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logs.append({
                    "filename": file.name,
                    "timestamp": data.get("timestamp"),
                    "target": data.get("target"),
                    "tool": data.get("tool"),
                    "risk": "Desconhecido"
                })
                # Tenta extrair o risco da análise
                analysis = data.get("antigravity_analysis", "")
                for risk in ["Crítico", "Alto", "Médio", "Baixo"]:
                    if risk.lower() in analysis.lower():
                        logs[-1]["risk"] = risk
                        break
        except Exception as e:
            print(f"Erro ao ler log {file}: {e}")
            
    return jsonify(logs)

@app.route('/api/logs/<filename>')
def get_log(filename):
    file_path = LOG_DIR / filename
    if not file_path.exists():
        abort(404)
        
    with open(file_path, 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))

def stream_output(process):
    """Lê a saída do processo e envia para o frontend via SocketIO."""
    for line in iter(process.stdout.readline, ''):
        socketio.emit('terminal_output', {'line': line})
        socketio.sleep(0) # Permite que o SocketIO processe a fila de emissão
    process.wait()
    socketio.emit('terminal_output', {'line': '\n--- SCAN FINALIZADO ---'})

@app.route('/api/logs/<filename>', methods=['DELETE'])
def delete_log(filename):
    file_path = LOG_DIR / filename
    if not file_path.exists():
        abort(404)
    
    try:
        file_path.unlink()
        return jsonify({"status": "Log deletado com sucesso", "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scan', methods=['POST'])
def run_scan():
    data = request.json
    tool = data.get('tool')
    target = data.get('target')
    
    if not tool or not target:
        return jsonify({"error": "Parâmetros inválidos"}), 400
        
    try:
        # Comando para rodar o scanner no modo não-interativo usando as flags --tool e --target
        # Usamos -u para output unbuffered e stdbuf para ferramentas externas
        cmd = ["stdbuf", "-oL", os.sys.executable, "-u", str(BASE_DIR / "scanner.py"), "--tool", tool, "--target", target]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )
        
        # Inicia thread para ler e enviar a saída
        thread = threading.Thread(target=stream_output, args=(process,))
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": "Scan iniciado", "tool": tool, "target": target})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

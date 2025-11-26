#!/usr/bin/env python3
"""Simple web interface for PixelPulseNeo control."""

import json
import socket
import os
import subprocess
from flask import Flask, render_template_string, request, jsonify, redirect, url_for

app = Flask(__name__)

IPC_PORT = 6000
SCHEDULE_FILE = os.path.expanduser("~/dev/PixelPulseNeo/schedule.json")

def send_ipc_command(command: str, args: list = [], kwargs: dict = {}) -> dict:
    """Send command to the IPC server."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("localhost", IPC_PORT))
        sock.settimeout(10)
        
        payload = json.dumps([command, args, kwargs])
        sock.send(payload.encode())
        
        response = sock.recv(8192).decode()
        sock.send(json.dumps(["disconnect", [], {}]).encode())
        sock.close()
        
        return json.loads(response)
    except Exception as e:
        return {"success": False, "error": str(e), "response": None}


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>PixelPulseNeo Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            margin: 0;
            padding: 20px;
        }
        h1 { color: #00d4ff; margin-bottom: 5px; }
        h2 { color: #888; font-size: 14px; margin-top: 0; }
        .container { max-width: 800px; margin: 0 auto; }
        .section {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .section h3 {
            margin-top: 0;
            color: #00d4ff;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }
        .btn {
            background: #0f3460;
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
            font-size: 14px;
            transition: background 0.2s;
        }
        .btn:hover { background: #1a5490; }
        .btn-danger { background: #c0392b; }
        .btn-danger:hover { background: #e74c3c; }
        .btn-success { background: #27ae60; }
        .btn-success:hover { background: #2ecc71; }
        .btn-warning { background: #f39c12; color: #000; }
        .btn-warning:hover { background: #f1c40f; }
        .command-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 10px;
        }
        .command-btn {
            background: #0f3460;
            padding: 15px 10px;
            text-align: center;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .command-btn:hover {
            background: #1a5490;
            transform: translateY(-2px);
        }
        .command-btn.active {
            background: #27ae60;
            box-shadow: 0 0 10px rgba(39, 174, 96, 0.5);
        }
        .schedule-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px;
            background: #0f3460;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .schedule-item input {
            width: 80px;
            padding: 5px;
            border: 1px solid #333;
            border-radius: 3px;
            background: #1a1a2e;
            color: #fff;
            text-align: center;
        }
        .status {
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        .status.success { background: rgba(39, 174, 96, 0.2); border: 1px solid #27ae60; }
        .status.error { background: rgba(192, 57, 43, 0.2); border: 1px solid #c0392b; }
        .current-info {
            background: #0f3460;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .current-info strong { color: #00d4ff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎛️ PixelPulseNeo Control</h1>
        <h2>LED Matrix Display Controller</h2>
        
        {% if message %}
        <div class="status {{ 'success' if success else 'error' }}">
            {{ message }}
        </div>
        {% endif %}
        
        <div class="section">
            <h3>📺 Current Status</h3>
            <div class="current-info">
                <strong>Now Playing:</strong> {{ current_command or 'Unknown' }}
            </div>
            <button class="btn btn-danger" onclick="restartService()">🔄 Restart Service</button>
            <button class="btn btn-warning" onclick="location.reload()">↻ Refresh</button>
        </div>
        
        <div class="section">
            <h3>🎬 Launch Command</h3>
            <p style="color: #888; font-size: 12px;">Click to launch immediately (runs for 60 seconds)</p>
            <div class="command-grid">
                {% for cmd in commands %}
                <div class="command-btn {{ 'active' if cmd == current_command else '' }}" 
                     onclick="launchCommand('{{ cmd }}')">
                    {{ cmd }}
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="section">
            <h3>⏱️ Schedule</h3>
            <form method="POST" action="/save_schedule">
                {% for item in schedule %}
                <div class="schedule-item">
                    <span style="flex: 1;">{{ item.command_name }}</span>
                    <input type="number" name="duration_{{ item.command_name }}" 
                           value="{{ item.duration|int }}" min="1" max="3600"> sec
                </div>
                {% endfor %}
                <button type="submit" class="btn btn-success">💾 Save Schedule</button>
            </form>
        </div>
    </div>
    
    <script>
        function launchCommand(cmd) {
            fetch('/launch/' + cmd)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Error: ' + data.error);
                    }
                });
        }
        
        function restartService() {
            if (confirm('Restart the PixelPulseNeo service?')) {
                fetch('/restart')
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        setTimeout(() => location.reload(), 3000);
                    });
            }
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    # Get list of commands
    result = send_ipc_command("ls")
    commands = result.get("response", []) if result.get("success") else []
    
    # Get current command
    current_result = send_ipc_command("get_current_command")
    current_command = None
    if current_result.get("success") and current_result.get("response"):
        current_command = current_result["response"].get("command_name")
    
    # Load schedule
    schedule = []
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            data = json.load(f)
            schedule = data.get("playlists", {}).get("default", {}).get("commands", [])
    except:
        pass
    
    return render_template_string(
        HTML_TEMPLATE,
        commands=sorted(commands),
        current_command=current_command,
        schedule=schedule,
        message=request.args.get('message'),
        success=request.args.get('success') == 'true'
    )


@app.route('/launch/<command>')
def launch(command):
    result = send_ipc_command("execute_now", [command, 60, True])
    return jsonify(result)


@app.route('/restart')
def restart():
    try:
        subprocess.run(["sudo", "systemctl", "restart", "pixel-pulse-neo.service"], check=True)
        return jsonify({"success": True, "message": "Service restarting... Page will refresh in 3 seconds."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/save_schedule', methods=['POST'])
def save_schedule():
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            data = json.load(f)
        
        commands = data.get("playlists", {}).get("default", {}).get("commands", [])
        
        for cmd in commands:
            key = f"duration_{cmd['command_name']}"
            if key in request.form:
                cmd['duration'] = float(request.form[key])
        
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        
        return redirect(url_for('index', message='Schedule saved! Restart service to apply.', success='true'))
    except Exception as e:
        return redirect(url_for('index', message=f'Error: {str(e)}', success='false'))


if __name__ == '__main__':
    print("Starting PixelPulseNeo Web Control on http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)

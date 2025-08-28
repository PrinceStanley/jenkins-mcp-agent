from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)
MASTER_URL = os.getenv('AGENT_MASTER_URL','http://agent-master:8082')

@app.post('/run')
def run():
    try:
        agents = requests.get(f"{MASTER_URL}/agents", timeout=10).json()
        text = request.get_json(force=True).get('input','')
        if agents:
            agent = agents[0]
            res = requests.post(f"http://{agent['service']}:8080/act",
                                json={'text': text}, timeout=10).json()
            return jsonify({'mcp':'ok','agent_used':agent,'response':res})
        return jsonify({'mcp':'no_agents','input':text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081)
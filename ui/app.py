from flask import Flask, render_template_string, request
import os, requests

app = Flask(__name__)
MCP_BASE_URL = os.getenv('MCP_BASE_URL', 'http://mcp:8081')
MASTER_BASE_URL = os.getenv('MASTER_BASE_URL', 'http://agent-master:8082')

PAGE = """
<h1>EKS Agents Demo</h1>
<form method="post" action="/create">
  <input name="name" placeholder="agent name" required />
  <input name="prompt" placeholder="agent prompt" required />
  <button>Create Agent</button>
</form>
<form method="post" action="/mcp">
  <input name="input" placeholder="ask MCP..." required />
  <button>Run MCP</button>
</form>
<pre>{{out}}</pre>
"""

@app.get("/")
def index():
    return render_template_string(PAGE, out="")

@app.post("/create")
def create():
    r = requests.post(f"{MASTER_BASE_URL}/agents",
                      json={"name": request.form["name"], "prompt": request.form["prompt"]},
                      timeout=120)
    return render_template_string(PAGE, out=r.text)

@app.post("/mcp")
def mcp():
    r = requests.post(f"{MCP_BASE_URL}/run", json={"input": request.form["input"]}, timeout=30)
    return render_template_string(PAGE, out=r.text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
from flask import Flask, request, jsonify
import os, subprocess, json
from jinja2 import Template

app = Flask(__name__)
WORKDIR = '/workspace'  # PVC mount
AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')
AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID', '111111111111')
NAMESPACE = os.getenv('NAMESPACE', 'ai-agents')
STATE_FILE = os.path.join(WORKDIR, 'agents.json')

def run(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed: {cmd}\n--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}")
    return res.stdout

def save_state(agents):
    with open(STATE_FILE,'w') as f: json.dump(agents, f)

def load_state():
    if not os.path.exists(STATE_FILE): return []
    try:
        with open(STATE_FILE,'r') as f: return json.load(f)
    except: return []

@app.get('/healthz')
def health(): return 'ok'

@app.get('/agents')
def list_agents(): return jsonify(load_state())

@app.post('/agents')
def create_agent():
    body = request.get_json(force=True)
    name = body['name'].lower().replace('_','-')
    prompt = body.get('prompt','hello')
    agent_dir = os.path.join(WORKDIR, name)
    os.makedirs(agent_dir, exist_ok=True)

    # Render templates
    with open(os.path.join('..','child_agent_template','Dockerfile.j2')) as f: dockerfile_j2 = f.read()
    with open(os.path.join('..','child_agent_template','agent.py.j2')) as f: agent_j2 = f.read()
    with open(os.path.join('..','child_agent_template','requirements.txt.j2')) as f: reqs_j2 = f.read()

    open(os.path.join(agent_dir,'Dockerfile'),'w').write(Template(dockerfile_j2).render())
    open(os.path.join(agent_dir,'agent.py'),'w').write(Template(agent_j2).render(agent_name=name, prompt=prompt))
    open(os.path.join(agent_dir,'requirements.txt'),'w').write(Template(reqs_j2).render())

    repo = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/child-agent-{name}"
    try:
        run(f"aws ecr describe-repositories --repository-names child-agent-{name} --region {AWS_REGION}")
    except:
        run(f"aws ecr create-repository --repository-name child-agent-{name} --region {AWS_REGION}")

    run(f"aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com")

    tag = f"{repo}:latest"
    run(f"docker build -t {tag} .", cwd=agent_dir)
    run(f"docker push {tag}")

    deploy_yaml = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-{name}
  namespace: {NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: agent-{name} }}
  template:
    metadata: {{ labels: {{ app: agent-{name} }} }}
    spec:
      containers:
        - name: agent
          image: {tag}
          ports: [{{ containerPort: 8080 }}]
---
apiVersion: v1
kind: Service
metadata:
  name: agent-{name}
  namespace: {NAMESPACE}
spec:
  selector: {{ app: agent-{name} }}
  ports:
    - port: 8080
      targetPort: 8080
  type: ClusterIP
"""
    man = os.path.join(agent_dir,'deploy.yaml')
    open(man,'w').write(deploy_yaml)
    run(f"kubectl apply -f {man} -n {NAMESPACE}")

    agents = [a for a in load_state() if a['name'] != name]
    record = {'name': name, 'image': tag, 'service': f'agent-{name}'}
    agents.append(record); save_state(agents)
    return jsonify(record)

if __name__ == '__main__':
    # NOTE: relies on DinD sidecar; DOCKER_HOST env set in Deployment to tcp://localhost:2375
    app.run(host='0.0.0.0', port=8082)
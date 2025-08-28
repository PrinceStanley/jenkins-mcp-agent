pipeline {
  agent any

  parameters {
    string(name: 'AWS_ACCOUNT_ID', defaultValue: '111111111111', description: 'AWS Account ID')
    string(name: 'AWS_REGION',     defaultValue: 'ap-south-1',    description: 'AWS Region')
    string(name: 'EKS_CLUSTER',    defaultValue: 'my-eks',        description: 'EKS cluster name')
    string(name: 'NAMESPACE',      defaultValue: 'ai-agents',     description: 'K8s namespace')
  }

  environment {
    ECR_UI_REPO        = "${params.AWS_ACCOUNT_ID}.dkr.ecr.${params.AWS_REGION}.amazonaws.com/ui"
    ECR_MCP_REPO       = "${params.AWS_ACCOUNT_ID}.dkr.ecr.${params.AWS_REGION}.amazonaws.com/mcp"
    ECR_MASTER_REPO    = "${params.AWS_ACCOUNT_ID}.dkr.ecr.${params.AWS_REGION}.amazonaws.com/agent-master"
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Login to ECR') {
      steps {
        sh '''
          aws ecr describe-repositories --repository-names ui || aws ecr create-repository --repository-name ui
          aws ecr describe-repositories --repository-names mcp || aws ecr create-repository --repository-name mcp
          aws ecr describe-repositories --repository-names agent-master || aws ecr create-repository --repository-name agent-master
          aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
        '''
      }
    }

    stage('Build & Push Images') {
      parallel {
        stage('UI') {
          steps {
            dir('ui') {
              sh '''
                docker build -t ${ECR_UI_REPO}:latest .
                docker push ${ECR_UI_REPO}:latest
              '''
            }
          }
        }
        stage('MCP') {
          steps {
            dir('mcp') {
              sh '''
                docker build -t ${ECR_MCP_REPO}:latest .
                docker push ${ECR_MCP_REPO}:latest
              '''
            }
          }
        }
        stage('Agent Master') {
          steps {
            dir('agent_master') {
              sh '''
                docker build -t ${ECR_MASTER_REPO}:latest .
                docker push ${ECR_MASTER_REPO}:latest
              '''
            }
          }
        }
      }
    }

    stage('Deploy to EKS') {
      steps {
        sh '''
          aws eks update-kubeconfig --name ${EKS_CLUSTER} --region ${AWS_REGION}
          kubectl apply -f k8s/00-namespace.yaml
          kubectl -n ${NAMESPACE} apply -f k8s/10-rbac-agent-master.yaml
          kubectl -n ${NAMESPACE} apply -f k8s/20-pvc-agent-master.yaml

          sed "s#REPLACE_UI_IMAGE#${ECR_UI_REPO}:latest#g" k8s/30-ui-deploy-svc.yaml | kubectl -n ${NAMESPACE} apply -f -
          sed "s#REPLACE_MCP_IMAGE#${ECR_MCP_REPO}:latest#g" k8s/31-mcp-deploy-svc.yaml | kubectl -n ${NAMESPACE} apply -f -
          sed "s#REPLACE_MASTER_IMAGE#${ECR_MASTER_REPO}:latest#g" k8s/32-agent-master-deploy-svc.yaml | \
            sed "s#REPLACE_AWS_REGION#${AWS_REGION}#g" | \
            sed "s#REPLACE_AWS_ACCOUNT_ID#${AWS_ACCOUNT_ID}#g" | \
            kubectl -n ${NAMESPACE} apply -f -

          kubectl -n ${NAMESPACE} apply -f k8s/90-ingress.yaml
        '''
      }
    }

    stage('(Optional) Seed a Child Agent') {
      when { expression { return params.SEED_NAME?.trim() } }
      steps {
        sh '''
          MASTER_SVC=$(kubectl -n ${NAMESPACE} get svc agent-master -o jsonpath='{.metadata.name}')
          # Access via ClusterIP from Jenkins if it can reach cluster network; else port-forward (example below):
          kubectl -n ${NAMESPACE} port-forward svc/${MASTER_SVC} 18082:8082 >/tmp/pf.log 2>&1 &
          sleep 3
          curl -s -X POST http://127.0.0.1:18082/agents -H 'content-type: application/json' \
            -d "{\"name\":\"${SEED_NAME}\",\"prompt\":\"hello from Jenkins\"}"
          pkill -f "port-forward.*${MASTER_SVC}" || true
        '''
      }
    }
  }

  parameters {
    string(name: 'SEED_NAME', defaultValue: '', description: 'Optionally create a child agent after deploy')
  }
}

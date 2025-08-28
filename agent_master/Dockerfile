FROM public.ecr.aws/docker/library/python:3.11-slim
RUN apt-get update && apt-get install -y curl jq && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# AWS CLI (v1 is fine for ECR login)
RUN pip install --no-cache-dir awscli==1.33.13
COPY app.py .
EXPOSE 8082
CMD ["python","app.py"]
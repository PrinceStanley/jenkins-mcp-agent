FROM public.ecr.aws/docker/library/python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY service.py .
EXPOSE 8081
CMD ["python","service.py"]
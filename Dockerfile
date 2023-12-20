FROM python:3.10-slim
EXPOSE 8080
ENV PROJECT_ID my-project-id \
    ZONE europe-west1-a \
    RESERVATION_ID test-reservation-id \
    MACHINE_TYPE e2-micro \
    TARGET_VM_COUNT 1 \
    GOOGLE_APPLICATION_CREDENTIALS /app/credentials.json \
    HOST_NAME 0.0.0.0 \
    PORT 8080
WORKDIR /app
ADD requirements.txt .
RUN pip install -r requirements.txt
ADD main.py .
CMD ["python", "main.py"]

FROM python:3.12-slim

# curl für die Übersetzungs- und Sprachausgabe-Anfragen
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server.py index.html ./

# Hugging Face Spaces erwartet Port 7860. DEEPL_API_KEY kommt aus den Space-Einstellungen (Secrets).
ENV PORT=7860
EXPOSE 7860
USER 1000
CMD ["python3", "-u", "server.py"]

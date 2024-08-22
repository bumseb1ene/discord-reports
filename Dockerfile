# Verwenden Sie ein offizielles Python-Image als Basis
FROM python:3.8

# Setzen Sie das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopieren Sie die 'requirements.txt' in den Container und installieren Sie die Abhängigkeiten
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Kopieren Sie den Rest des Projektverzeichnisses in den Container
COPY . .

# Führen Sie das Skript beim Start des Containers aus
CMD ["python","-u","./bot.py"]

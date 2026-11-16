# 1. L'image de base (Python 3.11 léger) - Basée sur Debian 13 (Trixie)
FROM python:3.11-slim

# 2. Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ACCEPT_EULA=Y

# 3. Installation du driver ODBC 18 pour SQL Server (Version Debian 13)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    apt-transport-https \
    unixodbc-dev \
    # On récupère les deux clés (l'ancienne et la nouvelle de 2025) pour être sûr
    && { curl -fsSL https://packages.microsoft.com/keys/microsoft.asc; \
         curl -fsSL https://packages.microsoft.com/keys/microsoft-2025.asc; } \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    # IMPORTANT : On pointe vers le dépôt Debian 13 (et non 11)
    && curl -fsSL https://packages.microsoft.com/config/debian/13/prod.list \
        -o /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# 4. Dossier de travail
WORKDIR /app

# 5. Installation des dépendances Python
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# 6. Copie du code
COPY . .

# 7. Sécurité : utilisateur non-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 8. Port
EXPOSE 8000

# 9. Démarrage
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
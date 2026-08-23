# Dockerfile cho NL2SQL Agent (ai/nl2sql/) - build tu thu muc goc repo:
#   docker build -f ai/Dockerfile -t nl2sql-agent .
# (khong build tu trong ai/ vi code dung package "ai.nl2sql", can ca thu muc ai/)

FROM python:3.11-slim

# Cai ODBC Driver 17 for SQL Server (can cho pyodbc ket noi SQL Server tu Linux)
# - Theo dung huong dan chinh thuc cua Microsoft cho Debian 12 (base image
#   python:3.11-slim hien dung Debian 12 "bookworm").
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates apt-transport-https \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc \
    && curl -sSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ai/requirements.txt ai/requirements.txt
RUN pip install --no-cache-dir -r ai/requirements.txt

COPY ai/ ai/

EXPOSE 5050
ENV WEBAPP_HOST=0.0.0.0
ENV WEBAPP_DEBUG=0

CMD ["python", "-m", "ai.nl2sql.webapp"]

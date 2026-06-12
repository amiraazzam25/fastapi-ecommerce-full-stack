FROM python:3.11-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y gnupg2 curl \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY main_app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the frontend static files
COPY frontend /app/frontend

# Copy the backend app
COPY main_app /app/main_app

# Set working directory to the backend so uvicorn runs correctly
WORKDIR /app/main_app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
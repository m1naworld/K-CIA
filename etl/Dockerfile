FROM python:3.11-slim

# System deps for GDAL/Fiona/GeoPandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev gcc g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY etl/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

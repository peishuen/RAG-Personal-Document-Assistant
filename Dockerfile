# this file builds the docker image for the app
# stage 1 builds the react frontend, stage 2 runs the python fastapi backend
# and serves the built frontend

# stage 1: build the react frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

# install node packages first so docker can cache this step
COPY frontend/package*.json ./
RUN npm install

# copy the frontend code and build it into static files
COPY frontend/ ./
RUN npm run build

# stage 2: run the python fastapi backend
FROM python:3.11-slim
WORKDIR /app

# install system tools, including tesseract for ocr
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# install python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy the source code and data
COPY src/ ./src/
COPY backend/ ./backend/
COPY data/ ./data/

# copy the built frontend from stage 1 into frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# create the data folders and allow the app to write to them
RUN mkdir -p data/uploads data/sessions data/chroma_db && chmod -R 777 data

# set the port (render uses $PORT, default is 10000)
ENV PORT=10000
EXPOSE 10000

# start the server on all network addresses
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]

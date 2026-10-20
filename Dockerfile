# this file builds the docker image for the fastapi backend
# the react frontend is deployed separately on cloudflare, so it is not built here

FROM python:3.11-slim
WORKDIR /app

# install system tools, including tesseract for ocr
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# install the cpu-only version of pytorch first, which is much smaller than the default one
# langchain-huggingface needs torch, and this server has no gpu
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# install python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy the source code
# the data folder is not copied, because docker-compose mounts it from your computer
COPY src/ ./src/
COPY backend/ ./backend/

EXPOSE 8000

# start the server on all network addresses inside the container
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

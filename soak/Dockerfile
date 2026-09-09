# Build context is the REPO ROOT (see soak/cloudbuild.yaml) so the image can
# reuse the guide's Python client instead of carrying a copy.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY soak/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY snippets/python/ge_streamassist.py /app/ge_streamassist.py
COPY soak/soak /app/soak
ARG GIT_SHA=dev
ENV GIT_SHA=${GIT_SHA}
ENTRYPOINT ["python", "-m", "soak"]
CMD ["run", "--tier", "fast"]

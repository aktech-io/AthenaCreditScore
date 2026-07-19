# syntax=docker/dockerfile:1
FROM python:3.12 AS syslibs

FROM python:3.12-slim

WORKDIR /app

# No apt layer: every dependency ships a prebuilt manylinux wheel, so the
# image needs no compiler. --only-binary keeps that true — a future dep
# without a wheel fails the build loudly instead of silently compiling.
# LightGBM's wheel needs the OpenMP runtime at import time; copy it from the
# full image rather than apt-get (slim lacks it, and apt mirrors are flaky).
COPY --from=syslibs /usr/lib/x86_64-linux-gnu/libgomp.so.1 /usr/lib/x86_64-linux-gnu/

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --only-binary :all: -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]

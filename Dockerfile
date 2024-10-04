ARG CUDA_VERSION="12.1.1"
ARG CUDNN_VERSION="8"
ARG UBUNTU_VERSION="22.04"
ARG MAX_JOBS=4

FROM nvidia/cuda:$CUDA_VERSION-cudnn$CUDNN_VERSION-devel-ubuntu$UBUNTU_VERSION AS base

# Install python 3.10
RUN apt-get update && apt-get install -y python3.10 \
    python3.10-dev python3.10-distutils python3.10-venv python3-pip git libreoffice

WORKDIR /app

ENV POETRY_VERSION="1.8.3"
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

ENV POETRY_CACHE_DIR=/tmp/poetry_cache
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_VIRTUALENVS_CREATE=true

FROM base AS packages

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ libc-dev \
    libffi-dev libgmp-dev libmpfr-dev libmpc-dev

COPY pyproject.toml poetry.lock ./
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && \
    pip install torch torchvision torchaudio && \
    pip install flash-attn
RUN poetry install --sync --no-cache --no-root --without=test

FROM base AS production

WORKDIR /app
ENV VIRTUAL_ENV=/app/.venv
COPY --from=packages ${VIRTUAL_ENV} ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN poetry self add "poetry-dynamic-versioning[plugin]"
COPY . /app/
RUN poetry install --without=test
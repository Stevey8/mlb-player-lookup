# Slim variant: full CPython + pip, without the extra OS build toolchain the
# default python:3.12 image carries. Smaller image, smaller attack surface.
FROM python:3.12-slim

# Don't write .pyc files (no benefit in a short-lived container) and don't
# buffer stdout/stderr, so `docker logs` / Render's log stream show output
# immediately instead of waiting on a buffer flush.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only the dependency manifest first and install. Docker caches layers
# by instruction + input hash, so as long as requirements.txt is unchanged,
# this layer (and the pip install) is reused on every later build even when
# application code below changes constantly.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code changes far more often than dependencies, so it's copied after —
# that keeps the expensive pip layer cached across code-only rebuilds.
# Copied explicitly (not `COPY . .`) so the gitignored, requests-dependent
# player_lookup_full.py reference file never ends up in the image.
COPY lookup.py web.py ./

# Create an unprivileged user and drop root. A container that runs as root
# gives any RCE/escape in the process more reach on the host than one
# running as a normal user — there's no reason this app needs root.
RUN groupadd --system app \
    && useradd --system --gid app --home /app --shell /usr/sbin/nologin app \
    && chown -R app:app /app
USER app

# Documents the default port for humans/tools reading the image; it does not
# publish the port by itself (`-p` / Render's routing does that).
EXPOSE 8000

# Local default so `docker run` just works without passing -e PORT. Render
# sets its own PORT value at runtime, which overrides this automatically.
ENV PORT=8000

# web.py reads $PORT and binds 0.0.0.0 whenever PORT is set in the
# environment, which it always is here — correct for both `docker run -p`
# locally and Render's dynamic port assignment.
CMD ["python", "web.py"]

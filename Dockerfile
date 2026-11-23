FROM python:3.12-alpine

LABEL org.opencontainers.image.title="Craft Web Server" \
      org.opencontainers.image.description="Host and update Craft web apps on a local network" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/zigh2/craft-web-server"

# Non-root user; /data holds apps.json, installed apps, cache, logs and the admin password hash.
RUN adduser -D -u 10001 craftweb && mkdir /data && chown craftweb /data
WORKDIR /app
COPY craftweb ./craftweb
COPY VERSION run.py ./

ENV CRAFTWEB_HOME=/data PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER craftweb
VOLUME /data
EXPOSE 8080 8081 8100-8119

HEALTHCHECK --interval=30s --timeout=4s --start-period=10s \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/health', timeout=3)"

ENTRYPOINT ["python", "-m", "craftweb"]
CMD ["serve"]

# Minimal Python image for the sandbox
FROM python:3.11-slim

# Avoid bytecode writes (useful with --read-only runs)
ENV PYTHONDONTWRITEBYTECODE=1

# Non-root user
RUN useradd -m runner
USER runner
WORKDIR /home/runner

# Copy the runner
COPY runner.py /home/runner/runner.py

# Run: reads base64 python from env CODE_B64 and prints stdout
ENTRYPOINT ["python", "/home/runner/runner.py"]

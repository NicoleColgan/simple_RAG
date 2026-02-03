# -----------------------------------------------------
    # Build stage
FROM dhi.io/python:3-debian12-dev AS build-stage

WORKDIR /build

COPY requirements.txt .

RUN pip install --user --no-cache-dir -r requirements.txt

# ---------------------------------------------------
    # Final Stage
    # uses same tag as build image but without `-dev` suffix
FROM dhi.io/python:3-debian12 AS runtime-stage

# new clean final directory
WORKDIR /app

# Copy packages installed in builder phase file system (root user) to non root home directory so we can use them in final phase
COPY --from=build-stage /root/.local /home/nonroot/.local

# Copy project files
COPY . .
# should we add venv to dockerignore to stop it being copied??? and maybe readme??

# Tell python where to find the libraries we just copied
ENV PATH=/home/nonroot/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Run python app directly with uvicorn module
# Bind to 0.0.0.0 so the app listens for external requests (from your computer), 
# and lock the port to 8000 to match the docker port mapping.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

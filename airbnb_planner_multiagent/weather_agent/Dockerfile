# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install nodejs & npm
RUN apt-get update && \
    apt-get install -y nodejs npm curl gcc libffi-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy environment file and requirements
COPY requirements.txt ./
COPY .env ./
COPY README.md ./

# Install uv
RUN pip install uv

# Install dependencies using uv (no lock file needed)
RUN uv pip install --system -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Define the command to run the application
CMD ["python", "__main__.py"]

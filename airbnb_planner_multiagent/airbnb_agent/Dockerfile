# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install nodejs & npm
RUN apt-get update && apt-get install -y nodejs npm curl && apt-get clean

# Install uv
RUN pip install --no-cache-dir uv

# Copy the requirements.txt file
COPY requirements.txt README.md .env ./

# Install dependencies
RUN uv pip install --system -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Define the command to run the application
CMD ["python", "__main__.py"]

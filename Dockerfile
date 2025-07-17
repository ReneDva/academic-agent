# Use a lightweight Python 3.10 base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy dependency file first to enable Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application directory into the container
COPY app/ app/

# Expose Flask's default port
EXPOSE 5000

# Start the application using Python's module execution
CMD ["python", "-m", "app.main"]

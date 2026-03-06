# Use an official lightweight Python 3.11 image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy all your project files into the container
COPY . .

# Install your Python dependencies
# This path must match the location of your requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Tell Docker that the container listens on port 7860
# Hugging Face exposes this port to the internet
EXPOSE 7860

# Command to run your application using Gunicorn
# This tells Gunicorn to run the 'app' variable from your 'backend/app.py' file
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "backend.app:app"]
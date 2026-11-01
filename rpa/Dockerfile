FROM python:3.12-slim

RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY rpa/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rpa/python_rpa_processor.py .

USER app
ENV PYTHONUNBUFFERED=1
CMD ["python", "python_rpa_processor.py"]

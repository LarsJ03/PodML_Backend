FROM python:3.11-slim

RUN pip install --no-cache-dir scikit-learn pandas joblib requests

WORKDIR /app
COPY train.py /app/train.py

# No volumes required if you use presigned URLs; for PV you can still read/write local paths.
CMD ["python", "-u", "train.py"]

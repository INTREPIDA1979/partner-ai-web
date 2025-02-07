FROM python:3.12

WORKDIR /app

ENV HOST 0.0.0.0

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8081

CMD streamlit run --server.port 8081 src/app.py
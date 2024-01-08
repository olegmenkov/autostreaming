FROM python:3.9
# set work directory
WORKDIR /usr/src/app/
# copy project
COPY . /usr/src/app/

# RUN pip install requirements
RUN pip install -r requirements.txt
# run app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
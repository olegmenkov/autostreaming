FROM python:3.11
# set work directory
WORKDIR /usr/src/app/
# copy project
COPY . /usr/src/app/

# RUN pip install requirements
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# run app
CMD ["python", "bot.py"]
FROM node

# Install pip
RUN apt-get update && apt-get install -y \
    python python-dev && \
    curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py && \
    python get-pip.py && \
    rm get-pip.py


# Create app dir
RUN mkdir /app
WORKDIR /app

# COPY project in app dir
COPY . .

# Install dependencies
## JS Dep
### Using Yarn
#RUN yarn
#RUN yarn global add concurrently
### Using NPM
RUN npm install
RUN npm install -g concurrently

# Pip requirements
RUN pip install -r requirements.txt


# Command
## Yarn
#CMD yarn __run_in_docker
CMD npm run __run_in_docker

FROM node

RUN apt-get update

# Install pip
RUN apt-get -y install python-pip

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

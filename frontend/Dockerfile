# Build stage
FROM dhi.io/node:25-debian12-dev AS build

WORKDIR /app

# Copy only dependency files first to leverage docker cache
COPY package*.json ./
RUN npm install

# Copy source code and build production assets
COPY . .
RUN npm run build

# STAGE 2: Production (The "Slim" stage)
# We dont need Node.js anymore, just a web server to serve the 'dist' folder
FROM dhi.io/nginx:1-debian12

# put build where nginx expects it
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
# The cmd is inherited from the base image so you usually dont have to rewrite it
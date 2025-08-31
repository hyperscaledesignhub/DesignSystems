# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY ui/package*.json ./
RUN npm install --only=production

# Copy source code
COPY ui/src/ ./src/
COPY ui/public/ ./public/

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built app
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config
COPY ui/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
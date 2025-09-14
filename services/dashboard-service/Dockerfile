FROM nginx:alpine

# Copy dashboard files
COPY services/dashboard-service/ /usr/share/nginx/html/

# Copy nginx configuration
COPY services/dashboard-service/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

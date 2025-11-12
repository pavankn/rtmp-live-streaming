FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential git wget libpcre3 libpcre3-dev zlib1g zlib1g-dev openssl libssl-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN git clone https://github.com/sergey-dryabzhinsky/nginx-rtmp-module.git && \
    wget http://nginx.org/download/nginx-1.25.5.tar.gz && \
    tar -xzf nginx-1.25.5.tar.gz && \
    cd nginx-1.25.5 && \
    ./configure --add-module=../nginx-rtmp-module --with-http_ssl_module && \
    make && make install

RUN apt-get update && apt-get install -y curl
RUN apt-get update && apt-get install -y iputils-ping dnsutils && rm -rf /var/lib/apt/lists/*

# RUN mkdir -p /usr/local/nginx/html/stream-dashboard
# RUN mkdir -p /usr/local/nginx/html/stream-dashboard/data
# RUN mkdir -p /usr/local/nginx/html/stream-dashboard/assets

COPY nginx.conf /usr/local/nginx/conf/nginx.conf

# COPY frontend/index.html /usr/local/nginx/html/stream-dashboard/index.html
# COPY frontend/main.js /usr/local/nginx/html/stream-dashboard/main.js
# COPY frontend/style.css /usr/local/nginx/html/stream-dashboard/style.css

# COPY frontend/assets /usr/local/nginx/html/stream-dashboard/assets
# COPY frontend/data   /usr/local/nginx/html/stream-dashboard/data

# Copy stat.xsl for RTMP stats page
WORKDIR /usr/local/nginx/html
RUN curl -L https://raw.githubusercontent.com/sergey-dryabzhinsky/nginx-rtmp-module/master/stat.xsl -o stat.xsl

RUN mkdir -p /worklogs

EXPOSE 1935
CMD ["/usr/local/nginx/sbin/nginx", "-g", "daemon off;"]


## Fluentd with elasticsearch and kibana + Nginx rate limit

Forked from: https://github.com/digikin/fluentd-elastic-kibana.git

### Docker-compose.yml
```
version: "3.7"
services:
  api_service:
    build:
      context: fastapi
      dockerfile: Dockerfile
    container_name: fastapi
    hostname: fastapi
    volumes:
      - ./fastapi:/code
    networks:
      - efk-net
      

  nginx:
    image: nginx
    container_name: nginx
    hostname: nginx
    ports:
      - "81:80"
    volumes:
      - ./nginx/config:/etc/nginx
      - ./nginx/log:/var/log/nginx
    networks:
      - efk-net
    depends_on:
      - api_service

  fluentd:
    build: ./fluentd
    container_name: fluentd
    hostname: fluentd
    volumes:
      - ./fluentd/conf:/fluentd/etc
      - ./nginx/log:/var/log/nginx
    depends_on:
      - elasticsearch
    ports:
      - "24224:24224"
      - "24224:24224/udp"
    networks:
      - efk-net

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.13.1
    container_name: elasticsearch
    hostname: elasticsearch
    environment:
      - "discovery.type=single-node"
    expose:
      - "9200"
    ports:
      - "9200:9200"
    volumes:
      - esdata:/usr/share/elasticsearch/data
    networks:
      - efk-net

  kibana:
    image: docker.elastic.co/kibana/kibana:7.13.1
    container_name: kibana
    hostname: kibana
    links:
      - "elasticsearch"
    ports:
      - "5601:5601"
    networks:
      - efk-net
volumes:
  esdata:
    driver: local

networks:
  efk-net:
    external: true
```
### fluent.conf
```
<source>
  @type tail
  path /var/log/nginx/access.log
  tag nginx
  pos_file /var/log/nginx/access.log.pos
  <parse>
     @type regexp
     #expression (?<clientip>[^ ]*) \[(?<timestamp>[^\]]*)\] \"(?<request>[^\]]*)\"
     #expression /^(?<message>[\s\S]+|(?<message1>[\s\S]+))/
     expression (?=^(?<message>[\s\S]+))(?=^(?<clientip>[^ ]*))
  </parse>
</source>

<source>
  @type tail
  path /var/log/nginx/error.log
  tag nginx
  pos_file /var/log/nginx/error.log.pos
  <parse>
     @type regexp
     expression ^\|(?<timestamp>(.*?))\|(?<log_level>(.*?))\|(?<uuid>(.*?))\|(?<clientip>(.*?))\|(?<agent>(.*?))\|(?<host>.*)\|(?<request>.*)\|(?<message>.*)
  </parse>
</source>

<match nginx>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name fluentd
  type_name nginx
  logstash_format true
  logstash_prefix ${tag}
  <buffer>
    flush_at_shutdown true
    flush_mode immediate
    flush_thread_count 8
    flush_thread_interval 1
    flush_thread_burst_interval 1
    retry_forever true
    retry_type exponential_backoff
   </buffer>
</match>
```
### Dockerfile 
```
FROM fluent/fluentd:v1.12.0-debian-1.0
USER root
RUN ["gem", "install", "fluent-plugin-elasticsearch", "--no-document", "--version", "5.0.3"]
USER fluent
```

### nginx.conf
```

worker_processes  1;

events {
  worker_connections  1024;  ## Default: 1024
}

http{
    limit_req_zone $request_uri zone=by_uri:10m rate=5r/s;

    upstream fastapi {
        server fastapi;
    }

    server {
        listen 80;

        location  ~* "^/article/([0-9]+)" {
            resolver 127.0.0.11;
            limit_req zone=by_uri;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;
            # we don't want nginx trying to do something clever with
            # redirects, we set the Host: header above already.
            proxy_redirect off;
            proxy_pass http://fastapi:8000/article/$1;
        }

        location ~* ^/article/burst/([0-9]+) {
            resolver 127.0.0.11;
            limit_req zone=by_uri burst=20;
            limit_req_log_level error;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;
            # we don't want nginx trying to do something clever with
            # redirects, we set the Host: header above already.
            proxy_redirect off;
            proxy_pass http://fastapi:8000/article/$1;
        }

        location ~* ^/article/nodelay/([0-9]+)  {
            resolver 127.0.0.11;
            limit_req zone=by_uri burst=20 nodelay;
            limit_req_log_level error;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;
            # we don't want nginx trying to do something clever with
            # redirects, we set the Host: header above already.
            proxy_redirect off;
            proxy_pass http://fastapi:8000/article/$1;
        }
    }

}
```

### Command
`docker-compose up -d`

If you alreay have the image and just want to rebuild fluentd with the new debian and gem version run:  
`docker-compose up -d --build`

### Site Info
- http://localhost:5601 (Kibana)
- http://localhost:81 (Webserver/Nginx)


### Test using Nginx Regex Parser

1. Run this command

```
for ((i=1;i<=500;i++)); do   curl -v --header "Connection: keep-alive" "localhost:81"; done > /dev/null 2>&1
```

### Load Testing
1. Install [Siege](https://github.com/JoeDog/siege) and run the command.
```
siege -R /usr/local/opt/siege/etc/siegerc -b -r 1 -c 100 http://localhost:81/article/burst/1100
```


### Reference
- https://www.nginx.com/blog/rate-limiting-nginx/
- https://www.freecodecamp.org/news/nginx-rate-limiting-in-a-nutshell-128fe9e0126c/
- https://dzone.com/articles/nginx-rate-limiting


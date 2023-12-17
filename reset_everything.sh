#! /bin/sh

docker-compose down
sudo chmod -R 777 ./data
docker volume rm bitcoin_janusgraph_btc_janusgraph_data
docker-compose up --build -d --remove-orphans

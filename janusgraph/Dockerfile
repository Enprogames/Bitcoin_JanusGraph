#  ./janusgraph/Dockerfile

FROM janusgraph/janusgraph:latest

# Copy the index creation script
COPY create_index.groovy /docker-entrypoint-initdb.d/create_index.groovy

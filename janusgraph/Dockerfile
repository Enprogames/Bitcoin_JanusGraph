#  ./janusgraph/Dockerfile

FROM janusgraph/janusgraph:latest

# "-Xmx8g -Xms8g" crashes the container, and "-XX:MaxPermSize=1024m" is not supported
# And I'm not sure what "-XX:MaxRAMPercentage=50" does
ENV JAVA_OPTS=" -Xss4096k "
ENV JAVA_OPTIONS="-Xss4096k"
ENV JVM_OPTS="-Xss4096k"

# Inspect RAM allocation
# docker-compose exec btc_janus bash -c "java -XX:+PrintFlagsFinal -version | grep -Ei 'maxheapsize|maxram'"
# COPY printSchema.groovy /opt/janusgraph/printSchema.groovy
# run using ./bin/gremlin.sh -e /opt/janusgraph/printSchema.groovy
# Copy the index creation script
COPY create_index.groovy /docker-entrypoint-initdb.d/create_index.groovy

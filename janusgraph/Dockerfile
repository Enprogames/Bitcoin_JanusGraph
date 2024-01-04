#  ./janusgraph/Dockerfile

FROM janusgraph/janusgraph:latest

# "-Xmx8g -Xms8g" crashes the container, and "-XX:MaxPermSize=1024m" is not supported
# And I'm not sure what "-XX:MaxRAMPercentage=50" does
ENV JAVA_OPTS=" -Xss2048k "
ENV JAVA_OPTIONS="-Xss2048k"
ENV JVM_OPTS="-Xss2048k"

# Inspect RAM allocation
# docker-compose exec btc_janus bash -c "java -XX:+PrintFlagsFinal -version | grep -Ei 'maxheapsize|maxram'"

# Copy the index creation script
COPY create_index.groovy /docker-entrypoint-initdb.d/create_index.groovy

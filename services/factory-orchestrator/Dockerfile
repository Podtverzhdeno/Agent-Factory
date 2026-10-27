# Railway preview image for the Control Plane, built from the MONOREPO root.
# Deploy only after exact SHA acceptance and owner ratification of ADR-0002.
FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY services/factory-orchestrator/pom.xml services/factory-orchestrator/pom.xml
COPY services/agent-store/src services/agent-store/src
COPY services/factory-orchestrator/src services/factory-orchestrator/src
COPY tests/control-plane/src tests/control-plane/src
# Testcontainers needs a Docker daemon, which a Dockerfile build cannot promise.
# This compilation/package step is NOT a release gate; run run-acceptance.sh on CI.
RUN mvn -B -ntp -f services/factory-orchestrator/pom.xml -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build --chown=10001:10001 \
  /workspace/services/factory-orchestrator/target/factory-orchestrator-0.1.0-SNAPSHOT.jar \
  /app/control-plane.jar
USER 10001:10001
EXPOSE 8080
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75"
ENTRYPOINT ["sh","-c","exec java -jar /app/control-plane.jar --server.port=${PORT:-8080}"]

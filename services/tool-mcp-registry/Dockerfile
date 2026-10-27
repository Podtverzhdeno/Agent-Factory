# Experimental single-module build recipe; NOT approved for production release.
# Railway should use /services/tool-mcp-registry as root only after ADR-0002 sign-off.
# A failing unit/integration test fails the container build; never use -DskipTests.
FROM maven:3.9-eclipse-temurin-21-noble AS verify
WORKDIR /workspace
COPY pom.xml ./
COPY src/ ./src/
RUN mvn -B -ntp -Dstyle.color=never clean verify

FROM eclipse-temurin:21-jre-noble AS runtime
WORKDIR /app
RUN groupadd --system --gid 10001 registry && \
    useradd --system --uid 10001 --gid registry --no-create-home registry
COPY --from=verify --chown=10001:10001 /workspace/target/tool-mcp-registry-0.1.0-SNAPSHOT.jar /app/registry.jar
USER 10001:10001
EXPOSE 8080
ENV JAVA_TOOL_OPTIONS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=70.0"
ENTRYPOINT ["java", "-jar", "/app/registry.jar"]

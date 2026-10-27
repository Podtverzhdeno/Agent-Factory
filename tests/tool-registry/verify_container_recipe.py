#!/usr/bin/env python3
"""Static safety checks for the isolated registry container recipe.

This does not replace `docker build` or `mvn clean verify` on a networked CI runner.
"""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
module = root / 'services' / 'tool-mcp-registry'
docker = (module / 'Dockerfile').read_text()
ignore = (module / '.dockerignore').read_text().splitlines()
instructions = '\n'.join(line for line in docker.splitlines() if line.strip() and not line.lstrip().startswith('#'))
project = ET.parse(module / 'pom.xml').getroot()
ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

checks = {
    'supported Spring Boot line': project.findtext('m:parent/m:version', namespaces=ns) == '4.1.2',
    'Maven tests required by build': 'mvn -B -ntp -Dstyle.color=never clean verify' in docker,
    'no Maven test skip': not any(token in instructions for token in ('-DskipTests', '-Dmaven.test.skip', '|| true')),
    'Java 21 builder and runtime': 'maven:3.9-eclipse-temurin-21-noble' in docker and 'eclipse-temurin:21-jre-noble' in docker,
    'no root runtime': 'USER 10001:10001' in docker,
    'no credentials in image instructions': not any(token in docker for token in ('ARG TOKEN', 'ARG SECRET', 'ENV JWT', 'ENV DATABASE_URL', 'COPY .env')),
    'Maven source and HTTP tests included': 'COPY src/ ./src/' in docker,
    'reproducible jar location': '/workspace/target/tool-mcp-registry-0.1.0-SNAPSHOT.jar' in docker,
    'no dynamic shell execution at runtime': 'ENTRYPOINT ["java", "-jar", "/app/registry.jar"]' in docker,
    'Railway production deployment not triggered from tests': not any(token in docker for token in ('railway up', 'railway redeploy', 'git push')),
    'sensitive file ignore': all(token in ignore for token in ('.env', '.env.*', '*.pem', '*.key', '*.p12')),
}
required = {
    'spring-boot-starter-webmvc',
    'spring-boot-starter-security',
    'spring-boot-starter-security-oauth2-resource-server',
    'spring-boot-starter-webmvc-test',
    'spring-boot-starter-security-test',
    'spring-boot-starter-test',
}
artifacts = {v.text for v in project.findall('m:dependencies/m:dependency/m:artifactId', ns)}
checks['current Boot 4 modular starters'] = required <= artifacts
checks['no deprecated OAuth2 starter'] = 'spring-boot-starter-oauth2-resource-server' not in artifacts

plugins = project.findall('m:build/m:plugins/m:plugin', ns)
surefire = next((p for p in plugins if p.findtext('m:artifactId', namespaces=ns) == 'maven-surefire-plugin'), None)
checks['Maven fails on absent JUnit tests'] = (surefire is not None and
    surefire.findtext('m:configuration/m:failIfNoTests', namespaces=ns) == 'true')
app_properties = (module / 'src/main/resources/application.properties').read_text()
checks['Railway injected PORT supported'] = 'server.port=${PORT:8080}' in app_properties
checks['graceful process shutdown'] = 'server.shutdown=graceful' in app_properties

failures = [label for label, passed in checks.items() if not passed]
if failures:
    for label in failures:
        print(f'FAIL: {label}', file=sys.stderr)
    raise SystemExit(1)
print(f'PASS: {len(checks)} static container safety and Maven recipe checks (build itself unverified)')

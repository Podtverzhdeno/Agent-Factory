#!/usr/bin/env python3
"""Offline architectural boundary checks; not a substitute for Maven or threat review."""
import pathlib
import re
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / 'services' / 'tool-mcp-registry'
DOMAIN = MODULE / 'src' / 'main' / 'java' / 'com' / 'agentfactory' / 'registry'
DOMAINS = ['ToolRegistry.java', 'PayloadShapeValidator.java',
           'MinimumCapabilityCover.java', 'BuilderManifestProjection.java']
for filename in DOMAINS:
    source = (DOMAIN / filename).read_text(encoding='utf-8')
    for imported in re.findall(r'^import\s+(?:static\s+)?([\w.*]+);', source, flags=re.MULTILINE):
        if not (imported.startswith('java.') or imported.startswith('com.agentfactory.registry.')):
            raise AssertionError(f'Domain leaked infrastructure dependency: {filename} imports {imported}')
    for network in ('java.net.', 'HttpClient', 'openConnection(', 'ProcessBuilder(', 'Runtime.getRuntime('):
        if network in source:
            raise AssertionError(f'Domain crossed outbound-network/process boundary: {filename}')

pom = ET.parse(MODULE / 'pom.xml').getroot()
ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
artifact = pom.find('./m:artifactId', ns)
assert artifact is not None and artifact.text == 'tool-mcp-registry'
version = pom.find('./m:parent/m:version', ns)
assert version is not None and version.text
java = pom.find('./m:properties/m:java.version', ns)
assert java is not None and int(java.text) >= 21

deps = {dep.find('m:artifactId', ns).text for dep in pom.findall('./m:dependencies/m:dependency', ns)}
assert {'spring-boot-starter-web', 'spring-boot-starter-security',
        'spring-boot-starter-oauth2-resource-server',
        'spring-boot-starter-test', 'spring-security-test'} <= deps

controller = (DOMAIN / 'RegistryApi.java').read_text(encoding='utf-8')
api = (MODULE / 'openapi.yaml').read_text(encoding='utf-8')
paths = set(re.findall(r'^  (/v0/registry/[^:]+):', api, flags=re.MULTILINE))
base = '/v0/registry'
controller_routes = set()
for method, local in re.findall(r'@(PostMapping|GetMapping)\("([^"]+)"\)', controller):
    controller_routes.add(base + local)
assert controller_routes == paths, (
    f'OpenAPI and HTTP adapter route mismatch: {sorted(controller_routes ^ paths)}'
)
# All references in the standalone runner must exist. This prevents a green SDD-only
# workflow from concealing a missing Java test source in the PR.
runner = (ROOT / 'tests' / 'tool-registry' / 'run.sh').read_text(encoding='utf-8')
referenced = re.findall(r'"\$ROOT/([^"\n]+\.(?:java|py))"', runner)
assert referenced, 'Test runner declares no source files'
for relative in referenced:
    assert (ROOT / relative).is_file(), f'Test runner references missing source: {relative}'
for test_file in (ROOT / 'tests' / 'tool-registry').glob('Registry*Test.java'):
    assert test_file.name in runner, f'Test runner skips security/component test: {test_file.name}'

assert 'anyRequest().denyAll()' in (DOMAIN / 'RegistrySecurity.java').read_text(encoding='utf-8')
print(f'PASS: Java domain architecture boundary ({len(DOMAINS)} modules), '
      f'JWT-deny-all default, {len(paths)} HTTP/OpenAPI path mappings, '
      f'{len(referenced)} verified runner source references, Maven dependencies')
print(f'GATE OPEN: Spring Boot parent {version.text} requires supported-line migration and Maven/JWT tests')

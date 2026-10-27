"""Guard source integrity to prevent duplicate/unterminated agent modules."""

from pathlib import Path

import ast


def test_builder_file_has_single_definition_set():
    base = Path(__file__).resolve().parents[2]
    source = base / 'services/agent-builder/agent_builder/core.py'
    tree = ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
    names = [node.name for node in tree.body
             if isinstance(node, (ast.ClassDef, ast.FunctionDef))]
    required = {'ToolManifest', 'ToolBinding', 'AgentSpec', 'BuildCommand',
                'Builder', 'TaskSnapshot'}
    for name in required:
        assert names.count(name) == 1, f'Expected exactly one {name} definition'


def test_component_python_sources_parse_independently():
    base = Path(__file__).resolve().parents[2]
    for folder in ('agent-builder', 'agent-runtime', 'litellm-adapter'):
        for source in (base / 'services' / folder).rglob('*.py'):
            ast.parse(source.read_text(encoding='utf-8'), filename=str(source))

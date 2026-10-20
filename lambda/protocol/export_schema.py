"""Exports protocol/v2.schema.json from the pydantic models.

    python -m protocol.export_schema          # rewrite the file
    python -m protocol.export_schema --check  # fail if the file is stale
"""
import json
import os
import sys

from protocol.models import Protocol

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v2.schema.json')


def render() -> str:
    schema = Protocol.model_json_schema(by_alias=True, mode='serialization')
    schema = {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        **schema,
        'title': 'Word Chain protocol v2',
    }
    return json.dumps(schema, indent=2, ensure_ascii=False) + '\n'


def main(argv) -> int:
    expected = render()
    if '--check' in argv:
        with open(SCHEMA_PATH, encoding='utf-8') as f:
            if f.read() != expected:
                print('protocol/v2.schema.json is stale; run python -m protocol.export_schema')
                return 1
        return 0
    with open(SCHEMA_PATH, 'w', encoding='utf-8', newline='\n') as f:
        f.write(expected)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

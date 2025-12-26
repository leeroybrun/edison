import json
from argparse import Namespace


def test_memory_search_returns_no_hits_by_default(project_root, monkeypatch, capsys):
    monkeypatch.chdir(project_root)

    from edison.cli.memory import search as memory_search

    args = Namespace(query="anything", limit=5, json=True, repo_root=str(project_root))
    rc = memory_search.main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 0
    assert payload["hits"] == []


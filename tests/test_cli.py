from jobfinder.cli import main


def test_run_command_with_no_sources_prints_zero_total(tmp_path, capsys, monkeypatch, database_url):
    sources_file = tmp_path / "sources.toml"
    sources_file.write_text("")
    monkeypatch.setenv("DATABASE_URL", database_url)

    main(["run", "--sources-file", str(sources_file)])

    assert capsys.readouterr().out == "0 jobs total (0 new)\n"

from jobfinder.cli import main


def test_run_command_with_no_sources_prints_zero_total(tmp_path, capsys):
    sources_file = tmp_path / "sources.toml"
    sources_file.write_text("")

    main(["run", "--sources-file", str(sources_file)])

    assert capsys.readouterr().out == "0 jobs total\n"

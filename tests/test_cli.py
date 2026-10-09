from jobfinder.cli import main


def test_run_command_with_no_boards_prints_zero_total(tmp_path, capsys):
    boards_file = tmp_path / "boards.toml"
    boards_file.write_text("")

    main(["run", "--boards-file", str(boards_file)])

    assert capsys.readouterr().out == "0 jobs total\n"

from jobfinder.cli import main


def test_run_command_with_no_boards_prints_zero_total(tmp_path, capsys):
    boards = tmp_path / "boards.toml"
    boards.write_text("")

    main(["run", "--boards", str(boards)])

    assert capsys.readouterr().out == "0 jobs total\n"

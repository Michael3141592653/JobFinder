from jobfinder.cli import main


def test_run_command_prints_placeholder(capsys):
    main(["run"])

    assert "nothing to run yet" in capsys.readouterr().out

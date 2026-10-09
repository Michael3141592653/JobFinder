from jobfinder.cli import main


def test_run(capsys):
    main(["run"])
    assert "jobfinder" in capsys.readouterr().out

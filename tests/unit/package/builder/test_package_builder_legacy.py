import os


def test_verbose_legacy_build(initproj, mock_venv, cmd):
    initproj(
        "example123-0.5",
        filedefs={
            "tox.ini": """
                    [tox]
                    isolated_build = false
                    """,
        },
    )
    result = cmd("--sdistonly", "-vvv", "-e", "py")
    assert "running sdist" in result.out, result.out
    assert "running egg_info" in result.out, result.out
    assert f"Writing example123-0.5{os.sep}setup.cfg" in result.out, result.out

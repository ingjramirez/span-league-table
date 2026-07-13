"""The command line: filenames or stdin/stdout, and honest exit codes."""

import io
import os
import subprocess
import sys

from league_table import __version__
from league_table.cli import (
    EXIT_BROKEN_PIPE,
    EXIT_INVALID_INPUT,
    EXIT_OK,
    main,
)

HEADER = "home_team,away_team,home_goals,away_goals\n"
RESULTS = HEADER + "Ipswich Town,Chelsea,3,1\nEverton,Arsenal,2,2\n"


def run(argv, stdin=""):
    """Run the CLI in-process, returning (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, stdin=io.StringIO(stdin), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


# --------------------------------------------------------------------------
# The happy paths: every combination of stream and file.
# --------------------------------------------------------------------------


def test_reads_stdin_and_writes_stdout_when_given_no_filenames():
    code, out, err = run([], stdin=RESULTS)

    assert code == EXIT_OK
    assert err == ""
    assert out.splitlines()[0].startswith("Position,Team,Played")
    assert "Ipswich Town" in out


def test_reads_a_named_input_file(tmp_path):
    source = tmp_path / "results.csv"
    source.write_text(RESULTS)

    code, out, _ = run([str(source)])

    assert code == EXIT_OK
    assert "Ipswich Town" in out


def test_writes_a_named_output_file(tmp_path):
    source = tmp_path / "results.csv"
    source.write_text(RESULTS)
    destination = tmp_path / "table.csv"

    code, out, _ = run([str(source), "-o", str(destination)])

    assert code == EXIT_OK
    assert out == ""  # nothing on stdout; it all went to the file
    assert destination.read_text().splitlines()[1].startswith("1,Ipswich Town")


def test_a_dash_means_stdin_explicitly():
    code, out, _ = run(["-"], stdin=RESULTS)

    assert code == EXIT_OK
    assert "Ipswich Town" in out


def test_the_table_is_ordered_by_the_1974_75_rules():
    code, out, _ = run([], stdin=RESULTS)

    teams = [line.split(",")[1] for line in out.splitlines()[1:]]

    # Ipswich win (2pts); Everton and Arsenal draw (1pt each, 2/2 = 1.000 average
    # apiece, so alphabetical); Chelsea lose.
    assert teams == ["Ipswich Town", "Arsenal", "Everton", "Chelsea"]


def test_a_pretty_table_is_printed_with_exact_alignment():
    """The layout is asserted character for character, on purpose.

    A formatter is only pinned by its exact output. Asserting merely that the
    column names appear and there is no comma would pass even with the
    alignment inverted -- club names right-aligned, numbers left-aligned -- which
    is a wrecked table that still contains all the right words.
    """
    code, out, _ = run(["--pretty"], stdin=RESULTS)

    assert code == EXIT_OK
    assert out == (
        "Pos  Team          P  W  D  L  F  A   GAvg  Pts\n"
        "  1  Ipswich Town  1  1  0  0  3  1  3.000    2\n"
        "  2  Arsenal       1  0  1  0  2  2  1.000    1\n"
        "  3  Everton       1  0  1  0  2  2  1.000    1\n"
        "  4  Chelsea       1  0  0  1  1  3  0.333    0\n"
    )


def test_the_pretty_table_widens_to_fit_a_long_club_name():
    # Pins the column-width computation, which is otherwise only ever exercised
    # by names that happen to be shorter than the header.
    code, out, _ = run(
        ["--pretty"], stdin=HEADER + "Wolverhampton Wanderers,Queens Park Rangers,1,0\n"
    )

    assert code == EXIT_OK
    assert out == (
        "Pos  Team                     P  W  D  L  F  A   GAvg  Pts\n"
        "  1  Wolverhampton Wanderers  1  1  0  0  1  0    inf    2\n"
        "  2  Queens Park Rangers      1  0  0  1  0  1  0.000    0\n"
    )


# --------------------------------------------------------------------------
# Failure. A wrong answer is worse than no answer, so these must not exit 0.
# --------------------------------------------------------------------------


def test_malformed_input_is_reported_on_stderr_with_a_non_zero_exit_code():
    code, out, err = run([], stdin=HEADER + "Everton,Arsenal,two,2\n")

    assert code == EXIT_INVALID_INPUT
    assert code != EXIT_OK
    assert out == ""  # no half-written table
    assert "line 2" in err
    assert "two" in err


def test_a_missing_input_file_is_reported_rather_than_crashing(tmp_path):
    code, out, err = run([str(tmp_path / "nope.csv")])

    assert code == EXIT_INVALID_INPUT
    assert out == ""
    assert "nope.csv" in err
    assert "Traceback" not in err


def test_an_unwritable_output_path_is_reported_rather_than_crashing(tmp_path):
    source = tmp_path / "results.csv"
    source.write_text(RESULTS)
    unwritable = tmp_path / "no-such-directory" / "table.csv"

    code, _, err = run([str(source), "-o", str(unwritable)])

    assert code == EXIT_INVALID_INPUT
    assert "table.csv" in err
    assert "Traceback" not in err


def test_a_bad_output_file_is_not_left_half_written(tmp_path):
    source = tmp_path / "results.csv"
    source.write_text(HEADER + "Everton,Arsenal,2,2\nBurnley,Stoke City,oops,1\n")
    destination = tmp_path / "table.csv"

    code, _, err = run([str(source), "-o", str(destination)])

    assert code == EXIT_INVALID_INPUT
    assert "line 3" in err
    assert not destination.exists()  # nothing written at all


def test_an_empty_input_is_rejected():
    code, _, err = run([], stdin="")

    assert code == EXIT_INVALID_INPUT
    assert "no header" in err.lower()


# --------------------------------------------------------------------------
# The real thing: a genuine subprocess, piping through the shell.
# --------------------------------------------------------------------------


def test_the_installed_command_works_as_a_unix_filter():
    completed = subprocess.run(
        [sys.executable, "-m", "league_table"],
        input=RESULTS,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.splitlines()[1].startswith("1,Ipswich Town")


def test_the_installed_command_exits_non_zero_on_bad_input():
    completed = subprocess.run(
        [sys.executable, "-m", "league_table"],
        input=HEADER + "Everton,Arsenal,two,2\n",
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "line 2" in completed.stderr


def test_the_module_entry_point_exposes_main():
    """`python -m league_table` runs this module.

    The two subprocess tests above prove it actually works end to end; coverage
    cannot see into a subprocess, so this imports it in-process as well. The
    `if __name__ == "__main__":` line itself is the one line in the codebase
    excluded from coverage -- it cannot run outside a real process launch.
    """
    import league_table.__main__ as entry_point

    assert entry_point.main is main


# --------------------------------------------------------------------------
# Behaving properly at the edges of a real unix environment.
# --------------------------------------------------------------------------


def test_a_file_written_by_excel_with_a_byte_order_mark_is_read(tmp_path):
    source = tmp_path / "excel.csv"
    source.write_text(RESULTS, encoding="utf-8-sig")  # what Excel writes

    code, out, err = run([str(source)])

    assert code == EXIT_OK, err
    assert "Ipswich Town" in out


def test_a_file_that_is_not_utf8_is_reported_rather_than_crashing(tmp_path):
    source = tmp_path / "latin1.csv"
    source.write_bytes(HEADER.encode() + "Atlético,Chelsea,1,0\n".encode("latin-1"))

    code, _, err = run([str(source)])

    assert code == EXIT_INVALID_INPUT
    assert "Traceback" not in err
    assert "utf-8" in err.lower() or "decode" in err.lower()


def test_unicode_club_names_survive_the_round_trip(tmp_path):
    source = tmp_path / "unicode.csv"
    source.write_text(HEADER + "Atlético,Beşiktaş,2,1\n", encoding="utf-8")
    destination = tmp_path / "table.csv"

    code, _, err = run([str(source), "-o", str(destination)])

    assert code == EXIT_OK, err
    assert "Atlético" in destination.read_text(encoding="utf-8")


def test_closing_the_pipe_early_is_not_an_error(tmp_path):
    """`league-table results.csv | head -1` must not blow up.

    The README calls this a unix filter, so it has to behave like one: a reader
    that stops early is a normal event, not a crash.

    The league here is deliberately enormous. A 22-club table is a couple of
    kilobytes, fits entirely inside the pipe buffer, and so never blocks on the
    write -- a small fixture would pass whether or not the bug were fixed.
    """
    big = tmp_path / "big.csv"
    big.write_text(
        HEADER + "".join(f"Club {n:05d},Club {n + 1:05d},1,0\n" for n in range(0, 8000, 2))
    )

    producer = subprocess.Popen(
        [sys.executable, "-m", "league_table", str(big)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    head = subprocess.Popen(
        ["head", "-1"], stdin=producer.stdout, stdout=subprocess.PIPE, text=True
    )
    producer.stdout.close()
    first_line = head.communicate()[0]
    producer.wait(timeout=10)
    errors = producer.stderr.read()
    producer.stderr.close()

    assert first_line.startswith("Position,Team")
    assert "BrokenPipeError" not in errors
    assert "Traceback" not in errors


def test_a_broken_pipe_on_a_stream_without_a_file_descriptor_is_handled():
    """The in-process half of the broken-pipe story.

    The subprocess test above proves the real `| head -1` case; this drives the
    same code path directly, including the branch where there is no fd to
    redirect (a StringIO has none).
    """

    class ClosedPipe(io.StringIO):
        def write(self, _text):
            raise BrokenPipeError(32, "Broken pipe")

    code = main([], stdin=io.StringIO(RESULTS), stdout=ClosedPipe(), stderr=io.StringIO())

    assert code == EXIT_BROKEN_PIPE


def test_a_broken_pipe_on_a_real_file_descriptor_is_handled():
    """The same, but over a genuine pipe whose reader has hung up.

    This is the branch that has a real fd, so /dev/null actually gets dup2'd over
    it -- the step that stops the interpreter's exit-time flush from raising a
    second BrokenPipeError and printing a traceback.
    """
    read_fd, write_fd = os.pipe()
    os.close(read_fd)  # nobody is listening

    with os.fdopen(write_fd, "w") as pipe:
        code = main([], stdin=io.StringIO(RESULTS), stdout=pipe, stderr=io.StringIO())

    assert code == EXIT_BROKEN_PIPE


# --------------------------------------------------------------------------
# Data quality: things that are suspicious but not necessarily wrong.
# --------------------------------------------------------------------------


def test_a_repeated_fixture_is_counted_but_warned_about():
    """The same fixture twice is the likeliest corruption in a results feed.

    It is not rejected: some leagues genuinely play the same pairing at the same
    ground more than once in a season, and this tool tabulates whatever league it
    is given. But it is the difference between a right and a wrong table, so it
    does not pass in silence.
    """
    code, out, err = run(
        [], stdin=HEADER + "Everton,Arsenal,2,1\nEverton,Arsenal,2,1\n"
    )

    assert code == EXIT_OK  # counted, not refused
    assert "Everton" in err and "Arsenal" in err
    assert "twice" in err or "2 times" in err
    assert out.splitlines()[1].startswith("1,Everton,2,2,0,0,4,2")  # both games counted


def test_a_clean_results_file_produces_no_warnings():
    _, _, err = run([], stdin=RESULTS)

    assert err == ""


def test_the_version_is_reported():
    # argparse's `version` action writes to the real sys.stdout and exits, so
    # this is only observable from an actual process.
    completed = subprocess.run(
        [sys.executable, "-m", "league_table", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert __version__ in completed.stdout


def test_the_help_text_names_the_historical_rules():
    completed = subprocess.run(
        [sys.executable, "-m", "league_table", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "goal average" in completed.stdout
    assert "two points for a win" in completed.stdout

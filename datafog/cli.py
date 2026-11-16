"""Console bootstrap with an actionable optional dependency error."""


def main():
    try:
        import typer  # noqa: F401
    except ImportError:
        import sys

        print(
            'The datafog command requires the CLI extra: pip install "datafog[cli]"',
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    from .client import app

    app()

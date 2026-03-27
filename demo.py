from littlebird.app import LittlebirdApplication, parse_options


def main() -> int:
    app = LittlebirdApplication(parse_options())
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())

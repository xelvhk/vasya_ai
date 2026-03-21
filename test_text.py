from utils.datetime_parser import parse_datetime


def main() -> None:
    samples = [
        "завтра в 15:00",
        "сегодня в 18:00",
        "послезавтра в 9:30",
        "25 марта в 14:00",
        "в пятницу в 19:00",
        "через 2 дня в 10:00",
        "завтра утром",
        "в пятницу вечером",
        "25 марта",
        "на следующей неделе",
        "в выходные",
        "когда-нибудь потом",
    ]

    for sample in samples:
        result = parse_datetime(sample)
        print(
            f"{sample!r} -> normalized={result.normalized}, "
            f"status={result.status}, message={result.message}"
        )


if __name__ == "__main__":
    main()

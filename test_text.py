from utils.datetime_parser import normalize_datetime


def main() -> None:
    samples = [
        "завтра в 15:00",
        "сегодня в 18:00",
        "послезавтра в 9:30",
        "25 марта в 14:00",
        "в пятницу в 19:00",
        "через 2 дня в 10:00",
        "25 марта",
        "когда-нибудь потом",
    ]

    for sample in samples:
        print(f"{sample!r} -> {normalize_datetime(sample)}")


if __name__ == "__main__":
    main()

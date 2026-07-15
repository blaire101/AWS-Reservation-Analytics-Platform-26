from pathlib import Path

import duckdb


TABLE_PATHS = {
    "ods_reservation_event": "aws/mock_data/ods/ods_reservation_event/part-00000.parquet",
    "ods_order": "aws/mock_data/ods/ods_order/part-00000.parquet",
    "dim_campaign": "aws/mock_data/dim/dim_campaign/part-00000.parquet",
}


def main() -> None:
    con = duckdb.connect()
    con.execute(Path("sql/local/00_mock_ods.sql").read_text(encoding="utf-8"))

    for table, relative_path in TABLE_PATHS.items():
        path = Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        con.execute(
            f"COPY {table} TO ? (FORMAT PARQUET)",
            [str(path)],
        )
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows -> {path}")


if __name__ == "__main__":
    main()

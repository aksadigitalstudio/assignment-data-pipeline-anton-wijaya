from pathlib import Path
from datetime import datetime
import pandas as pd

# Lokasi proyek dihitung dari lokasi file script.
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "data" / "raw" / "automobileEDA_dirty_training.csv"
OUTPUT_PATH = BASE_DIR / "data"/ "processed" / "automobileEDA_processed.csv"

def load_data(filepath):
    """Membaca CSV tanpa mengubah file mentah."""
    return pd.read_csv(filepath)

def inspect_data(df):
    """Menampilkan kondisi awal dataset."""
    print("\n=== LIMA BARIS PERTAMA ===")
    print(df.head().to_string())

    print("\n=== UKURAN DATA ===")
    print(f"Baris: {df.shape[0]}, Kolom: {df.shape[1]}")

    print("\n=== NAMA KOLOM DAN TIPE DATA ===")
    print(df.dtypes.to_string())

    print("\n=== MISSING VALUES PER KOLOM ===")
    print(df.isna().sum().to_string())

    print("\n=== JUMLAH BARIS DUPLIKAT ===")
    print(df.duplicated().sum())

    print("\n=== NILAI UNIK KOLOM TEKS ===")
    for column in df.select_dtypes(include=["object", "string"]).columns:
        print(f"\n{column}:")
        print(df[column].unique().tolist())

def parse_date(value):
    """Membaca tanggal sesuai empat format pada dataset."""
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()

    date_formats = [ 
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%d-%b-%Y",
    ]

    for date_format in date_formats:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue

    raise ValueError(f"format tanggal tidak dikenali: {value}")

def clean_data(df):
    """Menghapus duplikat persis dan merapikan kategori."""
    cleaned = df.copy()

    rows_before = len(cleaned)
    missing_before = cleaned.isna().sum().sum()

    # Hapus baris yang seluruh nilainya sama.
    cleaned = cleaned.drop_duplicates().copy()
    duplicates_removed = rows_before - len(cleaned)

    category_columns = [
        "make",
        "aspiration",
        "num-of-doors",
        "body-style",
        "drive-wheels",
        "engine-location",
        "engine-type",
        "num-of-cylinders",
        "fuel-system",
        "horsepower-binned",
    ]

    changed_column = []

    for column in category_columns:
        original = cleaned[column].copy()

        # StringDtype mempertahankan nilai kosong.
        cleaned[column] = (
            cleaned[column]
            .astype("string")
            .str.strip()
            .str.lower()
        )

        if not original.astype("string").equals(cleaned[column]):
            changed_column.append(column)

    print("\n=== CLEANING TAHAP 1 ===")
    print(f"Baris sebelum: {rows_before}")
    print(f"Duplikat dihapus: {duplicates_removed}")
    print(f"Baris sesudah: {len(cleaned)}")
    print(f"Missing values sebelum: {missing_before}")
    print(f"Missing values sesudah: {cleaned.isna().sum().sum()}")
    print(f"Kolom kategori berubah: {changed_column}")

    # Cleaning tahap 2: menangani nilai kosong.
    rows_before_stage2 = len(cleaned)
    missing_before_stage2 = cleaned.isna().sum().sum()

    # Harga kosong tidak diisi dengan harga buatan.
    cleaned = cleaned.dropna(subset=["price"]).copy()

    # Isi kolom numerik menggunakan median.
    for column in ["stroke", "horsepower"]:
        median_value = cleaned[column].median()
        cleaned[column] = cleaned[column].fillna(median_value)
        print(f"median {column}: {median_value}")

    # Isi jumlah pintu menggunakan kategori paling sering.
    doors_mode = cleaned["num-of-doors"].mode().iloc[0]
    cleaned["num-of-doors"] = (
        cleaned["num-of-doors"].fillna(doors_mode)
    )

    # Tandai Kategori yang belum di ketahui
    for column in ["make", "horsepower-binned"]:
        cleaned[column] = cleaned[column].fillna("unknown")

    print("\n=== CLEANING TAHAP 2 ===")
    print(f"Baris sebelum: {rows_before_stage2}")
    print(f"Baris tanpa harga dihapus: {rows_before_stage2 - len(cleaned)}")
    print(f"Baris sesudah: {len(cleaned)}")
    print(f"Missing values sebelum: {missing_before_stage2}")
    print(f"Missing values sesudah: {cleaned.isna().sum().sum()}")
    print(f"Modus jumlah pintu: {doors_mode}")

    print("\n=== SISA MISSING VALUE PER KOLOM ===")
    remaining_missing = cleaned.isna().sum()
    print(remaining_missing[remaining_missing > 0].to_string())  

    # Cleaning tahap 3: menyeragamkan tipe tanggal.
    dates_before = cleaned["transaction_date"].copy()  

    cleaned["transaction_date"] = pd.to_datetime(
        dates_before.map(parse_date)
    )

    date_comparison = pd.DataFrame({
        "sebelum": dates_before,
        "sesudah": cleaned["transaction_date"],
    })

    print("\n=== CLEANING TAHAP 3 ===")
    print(date_comparison.head().to_string(index=False))
    print(f"Tipe tanggal: {cleaned['transaction_date'].dtype}")
    print(f"Tanggal kosong: {cleaned['transaction_date'].isna().sum().sum()}")
    print(f"Jumlah baris: {len(cleaned)}")

    return cleaned

def transform_data(df):
    """Menambahkan normalisasi dan encoding kategori."""
    transformed = df.copy()

    # Min-Max Scaling horsepower.
    minimum = transformed["horsepower"].min()
    maximum = transformed["horsepower"].max()

    if maximum == minimum:
        transformed["horsepower_scaled"] = 0.0
    else:
        transformed["horsepower_scaled"] = (
            (transformed["horsepower"] - minimum)
            / (maximum - minimum)
        )

    # One-hot encoding tipe bodi.
    body_encoded = pd.get_dummies(
        transformed["body-style"],
        prefix="body",
        dtype=int,
    )

    transformed = pd.concat(
        [transformed, body_encoded],
        axis=1,
    )

    print("\n=== TRANSFORMASI DATA ===")
    print(f"Horsepower minimum: {minimum}")
    print(f" Horsepower maksimum: {maximum}")

    comparison_columns = [
        "horsepower",
        "horsepower_scaled",
        "body-style",
    ] + body_encoded.columns.tolist()

    print(transformed[comparison_columns].head().to_string(index=False))
    print(f"Baris sesudah transformasi: {len(transformed)}")
    print(f"Kolom sesudah transformasi : {transformed.shape[1]}")

    return transformed

def save_data(df, filepath):
    """Menyimpan hasil pipeline sebagai CSV baru"""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        filepath,
        index=False,
        date_format="%Y-%m-%d",
        encoding="utf-8",
    )

    print("\n=== PENYIMPANAN HASIL ===")
    print(f"File terimpan: {filepath}")
    print(f"Jumlah baris: {df.shape[0]}")
    print(f" Jumlah kolom: {df.shape[1]}")

def main():
    df = load_data(INPUT_PATH)
    inspect_data(df)

    df_cleaned = clean_data(df)
    df_transformed = transform_data(df_cleaned)

    save_data(df_transformed, OUTPUT_PATH)
    print("\nPipeline selesai.")

if __name__ == "__main__":
    main()

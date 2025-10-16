import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace, to_date, trim, when, year, month, sum as _sum

# ------------ 1: START SPARK SESSION ------------
spark = SparkSession.builder.appName("CAFC_Quarterly_Refinery_Pipeline").getOrCreate()

# ------------ 2: READ & CLEAN DATA ------------
# This requires manual download of the yyyy_QQ_cafc.tsv file from cafc open data portal

#import glob

#csv_files = glob.glob("posts/pyspark/data/*.tsv", recursive=True)

import os
from pathlib import Path

# List all csv files recursively
tsv_files = list(Path("data").rglob("*.tsv"))

# Get the file with the latest modification time

tsv_files = list(Path("data/").rglob("*.tsv"))

if tsv_files:
    recent_file = max(tsv_files, key=lambda f: os.path.getmtime(f))
    recent_file = str(recent_file)
    print(recent_file)
    df = spark.read.option("header", "true").option("delimiter", "\t").csv(recent_file)
else:
    print("No TSV files found.")


french_cols = [
    "Type de plainte recue", "Pays", "Province/Etat",
    "Categories thematiques sur la fraude et la cybercriminalite",
    "Methode de sollicitation", "Genre",
    "Langue de correspondance", "Type de plainte"
]
df = df.drop(*french_cols)

rename_map = {
    "Numero d'identification / Number ID": "id",
    "Date Received / Date recue": "date",
    "Complaint Received Type": "complaint_type",
    "Country": "country", "Province/State": "province",
    "Fraud and Cybercrime Thematic Categories": "fraud_cat",
    "Solicitation Method": "sol_method",
    "Gender": "gender", "Language of Correspondence": "lang_cor",
    "Victim Age Range / Tranche d'age des victimes": "age_range",
    "Complaint Type": "complaint_subtype",
    "Number of Victims / Nombre de victimes": "num_victims",
    "Dollar Loss /pertes financieres": "dollar_loss"
}
for old, new in rename_map.items():
    if old in df.columns:
        df = df.withColumnRenamed(old, new)

df = df.withColumn("num_victims",
    when(trim(col("num_victims")) == "", None).otherwise(col("num_victims").cast("integer")))
df = df.withColumn("dollar_loss",
    when(trim(col("dollar_loss")) == "", None)
    .otherwise(regexp_replace(col("dollar_loss"), "[$,]", "").cast("double")))

df = df.withColumn("date", to_date("date", "yyyy-MM-dd"))

# clean blank records
df = df.filter(df.country != "Not Specified") 
    #.show(truncate=False) 

# ------------ 3: DETECT QUARTER ------------
min_date = df.agg({"date": "min"}).collect()[0][0]
max_date = df.agg({"date": "max"}).collect()[0][0]
year_val = max_date.year
quarter_val = (max_date.month - 1) // 3 + 1
label = f"{year_val}_Q{quarter_val}"

out_dir = f"outputs_{label}"
os.makedirs(out_dir, exist_ok=True)

# ------------ 4: SAVE CLEANED DATA ------------
df.write.mode("overwrite").option("header", True).csv(f"{out_dir}/cleaned_cafc")

# ------------ 5: SUMMARIES ------------
monthly_summary = df.groupBy(year("date").alias("year"), month("date").alias("month")).agg(
    _sum("dollar_loss").alias("total_loss"),
    _sum("num_victims").alias("total_victims")
).orderBy("year", "month")
monthly_summary.write.mode("overwrite").option("header", True).csv(f"{out_dir}/monthly_summary")

yearly_summary = df.groupBy(year("date").alias("year")).agg(
    _sum("dollar_loss").alias("total_loss"),
    _sum("num_victims").alias("total_victims")
).orderBy("year")
yearly_summary.write.mode("overwrite").option("header", True).csv(f"{out_dir}/yearly_summary")


print(f"cafc_quarterly_fraud_data_pipeline.py script complete: {out_dir}")


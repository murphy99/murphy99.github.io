import os
import pandas as pd
import matplotlib.pyplot as plt
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace, to_date, trim, when, year, month, sum as _sum, desc
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# ------------ 1: START SPARK SESSION ------------
spark = SparkSession.builder.appName("CAFC_Quarterly_Fraud_Trends").getOrCreate()

# ------------ 2: READ & CLEAN DATA ------------
df = spark.read.option("header", "true").option("delimiter", "\t").csv("cafc.tsv")

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

pdf_monthly = monthly_summary.toPandas()
pdf_monthly["date"] = pd.to_datetime(pdf_monthly["year"].astype(str) + "-" + pdf_monthly["month"].astype(str) + "-01")
pdf_monthly = pdf_monthly.sort_values("date")
pdf_monthly["loss_3mo_avg"] = pdf_monthly["total_loss"].rolling(3, min_periods=1).mean()
pdf_monthly["victims_3mo_avg"] = pdf_monthly["total_victims"].rolling(3, min_periods=1).mean()

# ------------ 6: PEAKS ------------
max_loss_row = pdf_monthly.loc[pdf_monthly["total_loss"].idxmax()]
max_vict_row = pdf_monthly.loc[pdf_monthly["total_victims"].idxmax()]

# ------------ 7: TOP FRAUD CATEGORIES ------------
#df_quarter = df.filter((year(col("date")) == year_val) & ((month(col("date")) - 1) // 3 + 1 == quarter_val))
from pyspark.sql.functions import floor, month, year, col

df_quarter = df.filter(
    (year(col("date")) == year_val) &
    (floor((month(col("date")) - 1) / 3) + 1 == quarter_val)
)

top_fraud = df_quarter.groupBy("fraud_cat").agg(_sum("dollar_loss").alias("loss_total")) \
    .orderBy(desc("loss_total")).limit(3).toPandas()
top_cat_list = top_fraud["fraud_cat"].dropna().tolist()
top_fraud_str = "\n".join([f"{i+1}. {row['fraud_cat']} – ${row['loss_total']:,.0f}" for i, row in top_fraud.iterrows()])

# ------------ 8: CATEGORY CHARTS ------------
df_top_cats = df_quarter.filter(col("fraud_cat").isin(top_cat_list))
monthly_by_cat = df_top_cats.groupBy(year("date").alias("year"), month("date").alias("month"), "fraud_cat") \
    .agg(_sum("dollar_loss").alias("total_loss")).orderBy("year", "month")
pdf_by_cat = monthly_by_cat.toPandas()
pdf_by_cat["date"] = pd.to_datetime(pdf_by_cat["year"].astype(str) + "-" + pdf_by_cat["month"].astype(str) + "-01")

# Layered line chart
plt.figure(figsize=(12, 6))
for cat in top_cat_list:
    sub_df = pdf_by_cat[pdf_by_cat["fraud_cat"] == cat]
    plt.plot(sub_df["date"], sub_df["total_loss"], marker="o", label=cat)
plt.title(f"Top 3 Fraud Categories – {label}", fontsize=16)
plt.xlabel("Date")
plt.ylabel("Monthly Loss ($)")
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend()
layered_chart_path = f"{out_dir}/top3_fraud_categories_{label}.png"
plt.savefig(layered_chart_path, dpi=300)
plt.close()

# Stacked area chart
pdf_area = pdf_by_cat.pivot(index="date", columns="fraud_cat", values="total_loss").fillna(0)[top_cat_list]
pdf_area.plot.area(figsize=(12, 6), alpha=0.8)
plt.title(f"Top 3 Fraud Categories – Stacked Loss Trend ({label})", fontsize=16)
plt.xlabel("Date")
plt.ylabel("Monthly Loss ($)")
plt.grid(True, linestyle="--", alpha=0.4)
plt.legend(title="Fraud Category", loc="upper left")
stacked_chart_path = f"{out_dir}/top3_fraud_categories_stacked_{label}.png"
plt.savefig(stacked_chart_path, dpi=300)
plt.close()

# ------------ 9: MAIN DUAL-AXIS PEAK CHART ------------
fig, ax1 = plt.subplots(figsize=(12, 6))
ax1.set_xlabel("Date")
ax1.set_ylabel("Total Loss ($)", color="red")
ax1.plot(pdf_monthly["date"], pdf_monthly["total_loss"], color="red", marker="o", label="Total Loss ($)")
ax1.plot(pdf_monthly["date"], pdf_monthly["loss_3mo_avg"], color="darkred", linestyle="--", label="3-mo Avg Loss")
ax1.tick_params(axis="y", labelcolor="red")
ax1.annotate(f"Peak loss: ${max_loss_row['total_loss']:,.0f}",
             xy=(max_loss_row["date"], max_loss_row["total_loss"]),
             xytext=(max_loss_row["date"], max_loss_row["total_loss"]*1.15),
             arrowprops=dict(facecolor='black', arrowstyle="->"), ha="center")

ax2 = ax1.twinx()
ax2.set_ylabel("Total Victims", color="blue")
ax2.plot(pdf_monthly["date"], pdf_monthly["total_victims"], color="blue", marker="s", label="Total Victims")
ax2.plot(pdf_monthly["date"], pdf_monthly["victims_3mo_avg"], color="navy", linestyle="--", label="3-mo Avg Victims")
ax2.tick_params(axis="y", labelcolor="blue")
ax2.annotate(f"Peak victims: {max_vict_row['total_victims']:,}",
             xy=(max_vict_row["date"], max_vict_row["total_victims"]),
             xytext=(max_vict_row["date"], max_vict_row["total_victims"]*1.15),
             arrowprops=dict(facecolor='black', arrowstyle="->"), ha="center")

plt.title(f"Monthly Fraud Trends – Losses vs Victims ({label}, CAFC Data)", fontsize=16)
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
chart_path = f"{out_dir}/fraud_trends_{label}.png"
plt.savefig(chart_path, dpi=300)
plt.close()

# ------------ 10: PDF REPORT ------------
loss_month_name = max_loss_row["date"].strftime("%B %Y")
victim_month_name = max_vict_row["date"].strftime("%B %Y")
narrative = (
    f"In {label}, the Canadian Anti-Fraud Centre recorded its highest monthly financial loss "
    f"in {loss_month_name} at ${max_loss_row['total_loss']:,.0f}. "
    f"The month with the largest number of reported victims was {victim_month_name}, "
    f"with {max_vict_row['total_victims']:,} individuals impacted. "
    f"This quarter shows {'a strong divergence' if loss_month_name != victim_month_name else 'a parallel spike'}, "
    "highlighting potential changes in fraud targeting patterns."
)

pdf_path = f"{out_dir}/fraud_bulletin_{label}.pdf"
c = canvas.Canvas(pdf_path, pagesize=letter)
width, height = letter
c.setFont("Helvetica-Bold", 20)
c.drawString(50, height - 50, f"CAFC Quarterly Fraud Trends – {label}")
c.setFont("Helvetica", 10)
c.setFillGray(0.4)
c.drawString(50, height - 65, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
c.setFillColor(colors.black)

# Key stats
c.setFont("Helvetica-Bold", 12)
c.drawString(50, height - 100, "Key Highlights")
c.setFont("Helvetica", 12)
c.drawString(60, height - 120, f"Range: {min_date} - {max_date}")
c.drawString(60, height - 140, f"Peak Loss: ${max_loss_row['total_loss']:,.0f} ({loss_month_name})")
c.drawString(60, height - 160, f"Peak Victims: {max_vict_row['total_victims']:,} ({victim_month_name})")

# Narrative
c.setFont("Helvetica-Oblique", 11)
text_obj = c.beginText(50, height - 190)
for line in narrative.split(". "):
    text_obj.textLine(line.strip())
c.drawText(text_obj)

# Top fraud categories
c.setFont("Helvetica-Bold", 12)
c.drawString(50, height - 260, "Top 3 Fraud Categories This Quarter")
c.setFont("Helvetica", 11)
text_obj2 = c.beginText(60, height - 280)
for line in top_fraud_str.split("\n"):
    text_obj2.textLine(line)
c.drawText(text_obj2)

# Charts
c.drawImage(chart_path, 50, height - 550, width=width-100, height=200)
c.showPage()
c.drawImage(layered_chart_path, 50, height - 350, width=width-100, height=200)
c.drawImage(stacked_chart_path, 50, height - 600, width=width-100, height=200)

c.showPage()
c.save()

print(f"✅ Quarterly fraud trends package complete: {out_dir}")

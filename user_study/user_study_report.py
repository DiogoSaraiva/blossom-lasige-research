import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from fpdf import FPDF

# ====== CONFIG ======
CSV_FILE = "population.csv"
REPORT_FILE = "user_study_report.pdf"

# ====== LOAD DATA ======
df = pd.read_csv(CSV_FILE)

# ====== DESCRIPTIVE STATISTICS ======
desc_stats = df.describe(include='all')

# Save descriptive stats to CSV for reference
desc_stats.to_csv("descriptive_statistics.csv")

# ====== INFERENTIAL STATISTICS ======
# Example: correlation between switches and looking time front
pearson_corr, pearson_p = stats.pearsonr(df['switches'], df['time_front'])

# Example: t-test between front and side looking times
t_stat, t_p = stats.ttest_rel(df['time_front'], df['time_side'])

# ====== VISUALIZATIONS ======
sns.set(style="whitegrid")

# Emotion distribution
plt.figure(figsize=(6, 4))
sns.countplot(x='emotion', data=df, palette='pastel')
plt.title('Emotion Distribution')
plt.tight_layout()
plt.savefig("plot_emotion_distribution.png")
plt.close()

# Time looking boxplot
plt.figure(figsize=(6, 4))
sns.boxplot(data=df[['time_front', 'time_side']], palette='pastel')
plt.title('Time Looking Distribution')
plt.tight_layout()
plt.savefig("plot_time_boxplot.png")
plt.close()

# Correlation scatterplot
plt.figure(figsize=(6, 4))
sns.scatterplot(x='switches', y='time_front', data=df)
plt.title('Correlation: Switches vs Time Front')
plt.tight_layout()
plt.savefig("plot_correlation.png")
plt.close()

# ====== GENERATE PDF REPORT ======
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, "User Study Statistical Report", ln=True, align="C")
        self.ln(5)

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, title, ln=True)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('Helvetica', '', 10)
        self.multi_cell(0, 5, body)
        self.ln()

pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Intro
pdf.chapter_title("1. Introduction")
pdf.chapter_body("This report contains statistical analysis for the user study data, "
                 "including descriptive and inferential statistics, along with visualizations.")

# Descriptive statistics
pdf.chapter_title("2. Descriptive Statistics")
pdf.chapter_body(desc_stats.to_string())

# Inferential statistics
pdf.chapter_title("3. Inferential Statistics")
pdf.chapter_body(
    f"Pearson correlation between switches and time_front: r = {pearson_corr:.3f}, p = {pearson_p:.4f}\n"
    f"Paired t-test between time_front and time_side: t = {t_stat:.3f}, p = {t_p:.4f}"
)

# Visualizations
pdf.chapter_title("4. Visualizations")
for img in ["plot_emotion_distribution.png", "plot_time_boxplot.png", "plot_correlation.png"]:
    pdf.image(img, w=150)
    pdf.ln(5)

# Save PDF
pdf.output(REPORT_FILE)
print(f"Report generated: {REPORT_FILE}")

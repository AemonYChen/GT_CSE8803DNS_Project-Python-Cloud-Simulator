# This script visualizes the results from the comprehensive experiment.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# === Load the results from CSV ===
df = pd.read_csv("results.csv")

# Rename column for consistency
df.rename(columns={"energy_kwh": "Energy"}, inplace=True)

# === Create configuration Group column ===
def get_group(row):
    if not row["dvfs"] and row["migration"] == "disable":
        return "No DVFS / No Migration"
    elif row["dvfs"] and row["migration"] == "disable":
        return "DVFS / No Migration"
    elif not row["dvfs"] and row["migration"] == "default":
        return "No DVFS / Migration"
    elif row["dvfs"] and row["migration"] == "default":
        return "DVFS / Migration"

df["Group"] = df.apply(get_group, axis=1)

# Set global font sizes (for all future plots)
plt.rcParams.update({
    "axes.titlesize": 18,
    "axes.labelsize": 16,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14
})

# === Plot 1: Barplot of Energy by Group and Policy ===
group_order = [
    "No DVFS / No Migration", 
    "DVFS / No Migration", 
    "No DVFS / Migration", 
    "DVFS / Migration"
]

plt.figure(figsize=(14, 7))
sns.barplot(x="Group", y="Energy", hue="policy", data=df, order=group_order)
plt.title("Energy Consumption by Policy in Each Configuration Group")
plt.ylabel("Energy (kWh)")
plt.xlabel("Configuration Group")
plt.legend(title="Policy", loc='upper right', frameon=True)
plt.tight_layout()
plt.grid(axis='y')
plt.show()

# === Plot 2: Boxplot of Energy Distribution by Group ===
case_counts = df.groupby("Group")["Energy"].count().reindex(group_order)

plt.figure(figsize=(12, 6))
sns.boxplot(x="Group", y="Energy", data=df, order=group_order)
plt.title("Energy Consumption Distribution by Group (7 Cases Each)")
plt.ylabel("Energy (kWh)")
plt.xlabel("Configuration Group")
plt.grid(axis="y")
plt.tight_layout()
plt.show()
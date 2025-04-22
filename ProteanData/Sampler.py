import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

class ProteanSampler:
    def __init__(self,
                 lifetime_csv="ProteanData/VM_lifetime_blue_curve.csv",
                 arrival_csv="ProteanData/VM_arriving_rates.csv"):
        # Load lifetime data
        df_life = pd.read_csv(lifetime_csv)
        grouped = df_life.groupby('Lifetime (mins)', as_index=False).mean()
        self.x_vals = grouped['Lifetime (mins)'].values
        self.y_vals = grouped['Density (%)'].values
        self._build_pdf_cdf()

        # Load arrival rate data
        df_arr = pd.read_csv(arrival_csv)
        self.arrival_time = df_arr['Time (hours)'].values
        self.arrival_rates = df_arr['Normalized reqs/sec'].values / 100  # normalize to [0, 1]

    def _build_pdf_cdf(self):
        self.pdf_vals = self.y_vals / np.trapezoid(self.y_vals, np.log10(self.x_vals))
        self.log_x = np.log10(self.x_vals)
        delta_log_x = np.diff(np.concatenate([[self.log_x[0]], self.log_x]))
        self.cdf_vals = np.cumsum(self.pdf_vals * delta_log_x)
        self.cdf_vals /= self.cdf_vals[-1]
        self.inverse_cdf = interp1d(self.cdf_vals, self.log_x, bounds_error=False, fill_value="extrapolate")

    def VM_lifetime(self, n=1):
        u = np.random.uniform(0, 1, n)
        return 10 ** self.inverse_cdf(u)

    def plot_pdf_cdf(self):
        plt.figure(figsize=(10, 4))
        plt.subplot(1, 2, 1)
        plt.plot(self.x_vals, self.pdf_vals, label="PDF")
        plt.xscale('log')
        plt.xlabel("Lifetime (mins)")
        plt.ylabel("Probability Density")
        plt.title("PDF")
        plt.grid(True)
        plt.legend()

        plt.subplot(1, 2, 2)
        plt.plot(self.x_vals, self.cdf_vals, color='orange', label="CDF")
        plt.xscale('log')
        plt.xlabel("Lifetime (mins)")
        plt.ylabel("Cumulative Probability")
        plt.title("CDF")
        plt.grid(True)
        plt.legend()

        plt.tight_layout()
        plt.show()

    def plot_arrival_rates(self):
        if hasattr(self, 'arrival_rates') and hasattr(self, 'arrival_time'):
            plt.figure(figsize=(8, 4))
            plt.plot(self.arrival_time, self.arrival_rates, label="Arrival Rate")
            plt.xlabel("Time-of-day (hours)")
            plt.ylabel("Normalized reqs/sec")
            plt.title("Arrival Rate Profile")
            plt.ylim(0, 1.05)
            plt.grid(True)
            plt.tight_layout()
            plt.legend()
            plt.show()
        else:
            print("Arrival rates not loaded. Please check your CSV file.")

    def VM_arrival_rates(self, scale=1):
        arrival_numbers = np.round(self.arrival_rates * scale).astype(int)
        return arrival_numbers


# Example usage:
if __name__ == "__main__":
    sampler = ProteanSampler()
    samples = sampler.VM_lifetime(20)
    print("Generated Samples:", samples)
    sampler.plot_pdf_cdf()
    sampler.plot_arrival_rates()
    #breakpoint()

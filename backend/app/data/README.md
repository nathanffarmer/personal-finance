# Historical returns data

`historical_real_returns.csv` ships as a seeded, realistic-but-synthetic 100-year series with the following statistical properties:

- US equity: ~6.7% real annual mean, ~18% standard deviation
- 10y US Treasury: ~2% real annual mean, ~7% standard deviation
- Correlation: ~0.1

It is generated deterministically so unit tests can assert specific outputs.

To replace with real historical data, drop in a CSV with the same columns (`year,equity,bond`, all as decimal real returns). Recommended source: Robert Shiller's `ie_data.xls` (http://www.econ.yale.edu/~shiller/data.htm), processed to annual real total returns.

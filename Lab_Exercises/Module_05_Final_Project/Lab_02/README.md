# Module 05 Final Project - Lab 02: Creating Dashboard using Plotly and Dash

CISC7204 Assignment 02.

Completed from the course skeleton `DV0101EN-Final-Assign-Part-2-Questions.py` (TASK 2.1-2.6).

## Files

| file | role |
|---|---|
| `CISC7204 Assgn02 Module 05Final - Lab02.py` | the finished Dash application |
| `automobile-sales.csv` | the dataset, so the project space runs offline |
| `Screenshots/` | evidence of both report modes |
| `requirements.txt` | dependencies |

## Run

```
pip install -r requirements.txt
python "CISC7204 Assgn02 Module 05Final - Lab02.py"
```

Then open http://127.0.0.1:8050 .

## What the tasks became

- **2.1** `html.H1("Automobile Sales Statistics Dashboard")` with centred styling.
- **2.2** two dropdowns: `select-statistics` (Yearly / Recession) and `select-year` (1980-2023).
- **2.3** a `output-container` division that holds the two flex rows of charts.
- **2.4** the year dropdown is disabled unless "Yearly Statistics" is selected.
- **2.5** recession mode plots: mean sales per recession year (line), mean sales per
  vehicle type (bar), advertising-expenditure share per vehicle type (pie), and mean
  sales against the unemployment rate grouped by vehicle type (bar).
- **2.6** yearly mode plots: sales for the whole period (line), total sales by month
  (line), average sales per vehicle type in the chosen year (bar), and advertising
  expenditure per vehicle type in that year (pie).

## Verified

Driven headlessly with Playwright at 1600x1200: yearly mode for 1980 and 2015 and
recession mode each render four Plotly figures, and the year selector reports
`disabled=True` in recession mode. See `Screenshots/`.

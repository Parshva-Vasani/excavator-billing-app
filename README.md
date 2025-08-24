# 🚜 Excavators Billing Management System

A billing & analytics web app for excavator owners, built with **Streamlit**.

## Features

- Manage multiple users (clients).
- Record date-wise hours worked with ₹300/hr (editable).
- Auto-calculates total cost.
- Stores all data in CSV (`data/users.csv`, `data/entries.csv`).
- Detailed per-user view with download & delete options.
- Analysis dashboard:
  - Hours worked over time.
  - Monthly trends.
  - Weekday cost distribution.
  - User comparison.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

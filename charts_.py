import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import re
from datetime import datetime
import os
import logging


def load_budget_targets():
    """
    Load the budget targets data from the Excel file.
    Ensure the file exists in the repository under the specified directory.
    """
    # Define the file path
    file_path = os.path.join(os.path.dirname(__file__), 'budget_target_2425.xlsx')
    
    try:
        budget_df = pd.read_excel(file_path)
        budget_df.columns = budget_df.columns.str.strip()  # Strip column names of whitespace
        return budget_df
    except FileNotFoundError:
        st.error(f"❌ Budget file not found at {file_path}. Ensure it is correctly placed.")
        raise
    except Exception as e:
        st.error(f"❌ An error occurred while loading the budget file: {e}")
        raise




import re
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st

def generate_event_level_men_cumulative_sales_chart(filtered_data):
    """
    Generate a cumulative percentage-to-target sales chart for various competitions.
    """
    try:
        # --- 1️⃣ Load & normalize budget targets ---
        budget_df = load_budget_targets()
        budget_df.columns = budget_df.columns.str.strip()
        if "KickOff Event Start" in budget_df.columns:
            budget_df.rename(columns={"KickOff Event Start": "KickOffEventStart"}, inplace=True)
        budget_df["KickOffEventStart"] = pd.to_datetime(
            budget_df["KickOffEventStart"], errors="coerce", dayfirst=True
        ).dt.round("min")
        budget_df["Fixture Name"]     = budget_df["Fixture Name"].str.strip()
        budget_df["EventCompetition"] = budget_df["EventCompetition"].str.strip()

        # --- 2️⃣ Prepare your sales feed ---
        df = filtered_data.copy()
        df.columns = df.columns.str.strip()
        df["Fixture Name"]     = df["Fixture Name"].str.strip()
        df["EventCompetition"] = df["EventCompetition"].str.strip()
        df["PaymentTime"]      = pd.to_datetime(df["PaymentTime"], errors="coerce", dayfirst=True)
        df["KickOffEventStart"]= pd.to_datetime(df["KickOffEventStart"], errors="coerce", dayfirst=True).dt.round("min")
        df["IsPaid"]           = df["IsPaid"].astype(str).str.upper().fillna("FALSE")

        # --- 3️⃣ Merge on all three keys ---
        # --- 3️⃣ Merge against budget targets (keep all payment rows!) ---
        df = df.merge(
            budget_df,
            on=["Fixture Name","EventCompetition","KickOffEventStart"],
            how="left",
            validate="m:1"
        )
        if "Budget Target" not in df.columns:
            raise KeyError("After merge, 'Budget Target' missing – check your keys!")


        # --- 4️⃣ Filter & clean ---
        allowed = ['Premier League','UEFA Champions League','Carabao Cup','Emirates Cup','FA Cup']
        df = df[
            (df["IsPaid"]=="TRUE") &
            (df["EventCompetition"].isin(allowed))
        ].copy()
        df["Discount"] = df["Discount"].astype(str).str.lower()
        bad = ["credit","voucher","gift voucher","discount","pldl"]
        df = df[~df["Discount"].str.contains("|".join(map(re.escape,bad)), na=False)]

        # --- 5️⃣ Compute effective price & cumulative sums ---
        df["TotalEffectivePrice"] = np.where(
            df["TotalPrice"]>0,
            df["TotalPrice"],
            np.where(df["DiscountValue"].notna(), df["DiscountValue"], 0)
        )
        grouped = (
            df.groupby(["Fixture Name","EventCompetition","PaymentTime"])
              .agg(
                  DailySales=('TotalEffectivePrice','sum'),
                  KickOffDate=('KickOffEventStart','first'),
                  BudgetTarget=('Budget Target','first')
              )
              .reset_index()
        )
        grouped["CumulativeSales"]      = grouped.groupby(
            ["Fixture Name","EventCompetition"]
        )["DailySales"].cumsum()
        grouped["RevenuePercentage"]    = grouped["CumulativeSales"] / grouped["BudgetTarget"] * 100

        # --- 6️⃣ Plot ---
        competition_colors = {
            'Premier League':'green',
            'UEFA Champions League':'gold',
            'Carabao Cup':'blue',
            'Emirates Cup':'purple',
            'FA Cup':'pink'
        }
        abbreviations = {
            "Chelsea":"CHE","Tottenham":"TOT","Manchester United":"MANU",
            "West Ham":"WES","Paris Saint-Germain":"PSG","Liverpool":"LIV",
            # …
        }

        fig, ax = plt.subplots(figsize=(18,12))
        fig.patch.set_facecolor('#121212'); ax.set_facecolor('#121212')
        ax.tick_params(colors='white'); ax.spines['bottom'].set_color('white'); ax.spines['left'].set_color('white')

        now = pd.Timestamp.now()
        for (fx, comp), data in grouped.groupby(["Fixture Name","EventCompetition"]):
            opp     = fx.split(" v ")[-1]
            abbrev  = abbreviations.get(opp,opp[:3].upper())
            color   = competition_colors.get(comp,'blue')
            data    = data.sort_values("PaymentTime")
            kick    = data["KickOffDate"].iloc[0]
            pct     = data["RevenuePercentage"].iloc[-1]

            if kick < now:
                label, txt_col = f"{abbrev} ({comp[:3].upper()}, {pct:.0f}%)", 'red'
            else:
                days = (kick - now).days
                label, txt_col = f"{abbrev} ({comp[:3].upper()}, {days}d, {pct:.0f}%)", 'white'

            ax.plot(data["PaymentTime"].dt.date, data["RevenuePercentage"], label=label, color=color, linewidth=1)
            ax.text(data["PaymentTime"].dt.date.iloc[-1], pct, label, fontsize=12, color=txt_col)

        # dynamic x-axis
        udates = grouped["PaymentTime"].dt.date.nunique()
        if udates<=5:  ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        elif udates<=10: ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        else: ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b')); fig.autofmt_xdate()

        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,_: f'{int(x)}%'))
        ax.set_title("Cumulative Sales as % of Budget",fontsize=16,color='white')
        ax.set_xlabel("Date",color='white'); ax.set_ylabel("Revenue (% of Budget)",color='white')
        ax.axhline(100,color='red',linestyle='--',linewidth=1)

        handles = [
            plt.Line2D([0],[0],color=competition_colors[c],lw=2,label=c)
            for c in competition_colors
        ] + [plt.Line2D([],[],color='red',linestyle='--',label='Budget 100%')]
        ax.legend(handles=handles,loc='lower center',bbox_to_anchor=(0.5,-0.25),facecolor='black',labelcolor='white',ncol=3)

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Failed to generate men’s cumulative chart: {e}")
        logging.error(f"Error in generate_event_level_men_cumulative_sales_chart: {e}")



import re
import io
import base64
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def generate_event_level_women_cumulative_sales_chart(df, start_date, end_date):
    """
    Generate a cumulative percentage-to-target sales chart for Women's fixtures.
    """
    budget_df = load_budget_targets()

    # ─── Standardize column names ─────────────────────────────
    df.columns = df.columns.str.strip()
    budget_df.columns = budget_df.columns.str.strip()

    # ─── Rename the kickoff column safely ─────────────────────
    kickoff_col_df = next((col for col in df.columns if col.replace(" ", "").lower() == "kickoffeventstart"), None)
    if kickoff_col_df is None:
        raise ValueError("Missing expected column 'KickOffEventStart' in the main DataFrame.")
    elif kickoff_col_df != 'KickOffEventStart':
        df = df.rename(columns={kickoff_col_df: 'KickOffEventStart'})

    kickoff_col_budget = next((col for col in budget_df.columns if col.replace(" ", "").lower() == "kickoffeventstart"), None)
    if kickoff_col_budget is None:
        raise ValueError("Missing expected column 'KickOffEventStart' in the budget DataFrame.")
    elif kickoff_col_budget != 'KickOffEventStart':
        budget_df = budget_df.rename(columns={kickoff_col_budget: 'KickOffEventStart'})

    # ─── Normalize kickoff dates to remove time parts ─────────
    df['KickOffEventStart'] = pd.to_datetime(df['KickOffEventStart'], errors='coerce').dt.normalize()
    budget_df['KickOffEventStart'] = pd.to_datetime(budget_df['KickOffEventStart'], errors='coerce').dt.normalize()

    df['EventCompetition'] = df['EventCompetition'].str.strip()
    df['Fixture Name'] = df['Fixture Name'].str.strip()
    budget_df['EventCompetition'] = budget_df['EventCompetition'].str.strip()
    budget_df['Fixture Name'] = budget_df['Fixture Name'].str.strip()

    # ─── Merge budget targets ────────────────────────────────
    df = df.merge(budget_df, on=['Fixture Name', 'EventCompetition', 'KickOffEventStart'], how='left')

    start_date = pd.to_datetime('2024-06-17')
    df['PaymentTime'] = pd.to_datetime(df['PaymentTime'], errors='coerce')

    if 'Budget Target' not in df.columns:
        raise ValueError("The 'Budget Target' column is missing from the merged DataFrame. Please check the input budget file.")

    df['IsPaid'] = df['IsPaid'].astype(str).fillna('FALSE')

    allowed_competitions = ["Barclays Women's Super League", "UEFA Women's Champions League"]
    filtered_data = df[
        (df['PaymentTime'] >= start_date) &
        (df['PaymentTime'] <= end_date) &
        (df['IsPaid'].str.upper() == 'TRUE') &
        (df['EventCompetition'].isin(allowed_competitions))
    ].copy()

    filtered_data['Discount'] = filtered_data['Discount'].astype(str).str.lower().str.strip()
    exclude_keywords = ["credit", "voucher", "gift voucher", "discount", "pldl"]
    mask = ~filtered_data['Discount'].str.contains('|'.join([re.escape(k) for k in exclude_keywords]), na=False)
    filtered_data = filtered_data[mask]

    filtered_data['TotalEffectivePrice'] = np.where(
        filtered_data['TotalPrice'] > 0,
        filtered_data['TotalPrice'],
        filtered_data['DiscountValue'].fillna(0)
    )

    grouped_data = (
        filtered_data.groupby(['Fixture Name', 'EventCompetition', 'KickOffEventStart', 'PaymentTime'])
        .agg(
            DailySales=('TotalEffectivePrice', 'sum'),
            BudgetTarget=('Budget Target', 'first')
        )
        .reset_index()
    )

    if grouped_data.empty:
        print("No data available for women's chart after filtering.")
        return None

    grouped_data = grouped_data.sort_values(by=['Fixture Name', 'EventCompetition', 'KickOffEventStart', 'PaymentTime'])
    grouped_data['CumulativeSales'] = grouped_data.groupby(['Fixture Name', 'EventCompetition', 'KickOffEventStart'])['DailySales'].cumsum()
    grouped_data['RevenuePercentage'] = (grouped_data['CumulativeSales'] / grouped_data['BudgetTarget']) * 100

    competition_colors = {
        "Barclays Women's Super League": 'green',
        "UEFA Women's Champions League": 'gold'
    }
    abbreviations = {
        "Manchester City Women": "MCW", "Everton Women": "EVT", "Chelsea Women": "CHE",
        "Vålerenga Women": "VAL", "Brighton Women": "BRI", "Juventus Women": "JUV",
        "Aston Villa Women": "AST", "FC Bayern Munich Women": "BAY", "Tottenham Hotspur Women": "TOT",
        "Liverpool Women": "LIVW", "UWCL Quarter-Final (Date TBC)": "UWCL QF TBC"
    }

    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#121212')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')

    for (fixture_name, _, ko_date), fixture_data in grouped_data.groupby(['Fixture Name', 'EventCompetition', 'KickOffEventStart']):
        opponent = fixture_name.split(' v ')[-1]
        abbrev = abbreviations.get(opponent, opponent[:3].upper())
        event_comp = fixture_data['EventCompetition'].iloc[0]
        color = competition_colors.get(event_comp, 'white')

        fixture_data = fixture_data.sort_values('PaymentTime')
        cumulative_percentage = fixture_data['RevenuePercentage'].iloc[-1]

        if pd.notnull(ko_date) and ko_date < pd.Timestamp.now():
            abbrev += f" ({event_comp[:3].upper()}, {cumulative_percentage:.0f}%)"
            annotation_color = 'red'
            annotation_weight = 'bold'
        else:
            days_left = (ko_date - pd.Timestamp.now()).days if pd.notnull(ko_date) else 'TBD'
            abbrev += f" ({days_left} days, {cumulative_percentage:.0f}%)"
            annotation_color = 'white'
            annotation_weight = 'normal'

        ax.plot(
            fixture_data['PaymentTime'].dt.date,
            fixture_data['RevenuePercentage'],
            label=abbrev,
            color=color,
            linewidth=1.5
        )

        ax.text(
            fixture_data['PaymentTime'].dt.date.iloc[-1],
            fixture_data['RevenuePercentage'].iloc[-1],
            abbrev,
            fontsize=10,
            color=annotation_color,
            weight=annotation_weight
        )

    ax.set_title("AFC Women's Cumulative Revenue 24/25", fontsize=12, color='white')
    ax.set_xlabel("Date", fontsize=12, color='white')
    ax.set_ylabel("Revenue (% of Budget Target)", fontsize=12, color='white')
    ax.axhline(y=100, color='red', linestyle='--', linewidth=1)
    ax.grid(False)

    min_date = grouped_data['PaymentTime'].min().date()
    max_date = grouped_data['PaymentTime'].max().date()
    ax.set_xlim([min_date, max_date])

    ax.xaxis.set_major_locator(mdates.DayLocator(interval=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))

    handles = [
        plt.Line2D([0], [0], color='green', lw=2, label="Barclays Women's Super League"),
        plt.Line2D([0], [0], color='gold', lw=2, label="UEFA Women's Champions League"),
        plt.Line2D([], [], color='red', linestyle='--', linewidth=2, label='Budget Target (100%)')
    ]
    ax.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.25), fontsize=10, frameon=False, facecolor='black', labelcolor='white', ncol=3)

    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300)
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

import re
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st

def generate_event_level_concert_cumulative_sales_chart(filtered_data):
    """
    Generate a cumulative percentage-to-target sales chart for Concert events.
    """
    try:
        # --- 1️⃣ Load & normalize budget targets ---
        budget_df = load_budget_targets()
        # strip whitespace
        budget_df.columns = budget_df.columns.str.strip()
        # if your file calls it something else, rename here:
        if "KickOff Event Start" in budget_df.columns:
            budget_df.rename(columns={"KickOff Event Start": "KickOffEventStart"}, inplace=True)

        budget_df["KickOffEventStart"] = pd.to_datetime(
            budget_df["KickOffEventStart"], errors="coerce", dayfirst=True
        ).dt.round("min")

        # clean keys
        budget_df["Fixture Name"]     = budget_df["Fixture Name"].str.strip()
        budget_df["EventCompetition"] = budget_df["EventCompetition"].str.strip()

        # --- 2️⃣ Prepare your sales feed ---
        df = filtered_data.copy()
        df.columns = df.columns.str.strip()  # strip whitespace
        df["Fixture Name"]     = df["Fixture Name"].str.strip()
        df["EventCompetition"] = df["EventCompetition"].str.strip()
        df["EventCategory"]    = df["EventCategory"].str.strip()

        df["KickOffEventStart"] = pd.to_datetime(
            df["KickOffEventStart"], errors="coerce", dayfirst=True
        ).dt.round("min")

        # drop any accidental duplicates so merge works 1:1
        df = df.drop_duplicates(
            subset=["Fixture Name", "EventCompetition", "KickOffEventStart"], keep="first"
        )

        # --- 3️⃣ Merge on all three keys ---
        # --- 3️⃣ Merge against budget targets (keep all payment rows!) ---
        df = df.merge(
            budget_df,
            on=["Fixture Name","EventCompetition","KickOffEventStart"],
            how="left",
            validate="m:1"
        )
        if "Budget Target" not in df.columns:
            raise KeyError("After merge, 'Budget Target' missing – check your keys!")


        # --- 4️⃣ Parse PaymentTime + filter for paid concerts ---
        df["PaymentTime"] = pd.to_datetime(
            df["PaymentTime"], errors="coerce", dayfirst=True
        )
        df["IsPaid"] = df["IsPaid"].astype(str).str.upper().fillna("FALSE")

        df = df[
            (df["IsPaid"] == "TRUE") &
            (df["EventCategory"].str.lower() == "concert")
        ].copy()

        # --- 5️⃣ Exclude unwanted discounts ---
        df["Discount"] = df["Discount"].astype(str).str.lower()
        bad = ["credit", "voucher", "gift voucher", "discount", "pldl"]
        df = df[~df["Discount"].str.contains("|".join(map(re.escape, bad)), na=False)]

        # --- 6️⃣ Compute your effective price ---
        df["TotalEffectivePrice"] = np.where(
            df["TotalPrice"] > 0,
            df["TotalPrice"],
            np.where(df["DiscountValue"].notna(), df["DiscountValue"], 0)
        )

        # --- 7️⃣ Group & cumulative sums ---
        grouped = (
            df.groupby(["Fixture Name", "EventCompetition", "PaymentTime"])
              .agg(
                  DailySales=('TotalEffectivePrice', 'sum'),
                  KickOffDate=('KickOffEventStart', 'first'),
                  BudgetTarget=('Budget Target', 'first')
              )
              .reset_index()
        )
        grouped["CumulativeSales"] = grouped.groupby(
            ["Fixture Name", "EventCompetition"]
        )["DailySales"].cumsum()
        grouped["RevenuePercentage"] = (
            grouped["CumulativeSales"] / grouped["BudgetTarget"] * 100
        )

        # --- 8️⃣ Plotting ---
        fixture_colors = {
            "Robbie Williams Live 2025 (Friday)": 'cyan',
            "Robbie Williams Live 2025 - Saturday": 'magenta'
        }

        fig, ax = plt.subplots(figsize=(16, 10))
        fig.patch.set_facecolor('#121212')
        ax.set_facecolor('#121212')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')

        now = pd.Timestamp.now()
        for fx, data in grouped.groupby("Fixture Name"):
            color = fixture_colors.get(fx, 'blue')
            data = data.sort_values("PaymentTime")
            kick = data["KickOffDate"].iloc[0]
            pct  = data["RevenuePercentage"].iloc[-1]

            if kick < now:
                label, txt_col = f"{fx} (p, {pct:.0f}%)", 'red'
            else:
                days = (kick - now).days
                label, txt_col = f"{fx} ({days} days, {pct:.0f}%)", 'white'

            ax.plot(
                data["PaymentTime"].dt.date,
                data["RevenuePercentage"],
                label=label, color=color, linewidth=1.5
            )
            ax.text(
                data["PaymentTime"].dt.date.iloc[-1],
                pct, label, fontsize=10, color=txt_col
            )

        ax.set_title("Concert Cumulative Revenue 24/25", fontsize=12, color='white')
        ax.set_xlabel("Date", fontsize=12, color='white')
        ax.set_ylabel("Revenue (% of Budget Target)", fontsize=12, color='white')
        ax.axhline(y=100, color='red', linestyle='--', linewidth=1)

        # dynamic x‑axis
        min_d = grouped["PaymentTime"].min().date()
        max_d = grouped["PaymentTime"].max().date()
        ax.set_xlim(min_d, max_d)
        span = (max_d - min_d).days
        interval = 2 if span <= 30 else 10
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))

        handles = [
            plt.Line2D([0],[0],color='cyan',      lw=2, label="Robbie Williams Live - Friday"),
            plt.Line2D([0],[0],color='magenta',  lw=2, label="Robbie Williams Live - Saturday"),
            plt.Line2D([],[],  color='red', linestyle='--', linewidth=2, label='Budget Target (100%)'),
        ]
        ax.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.25),
                  fontsize=10, frameon=False)

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Failed to generate the concert cumulative chart: {e}")
        logging.error(f"Error in generate_event_level_concert_cumulative_sales_chart: {e}")




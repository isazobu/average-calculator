import streamlit as st
import pandas as pd
from io import StringIO


st.title('Average Cost Calculator')


if 'transactions' not in st.session_state:
    st.session_state.transactions = pd.DataFrame(columns=['Date', 'Shares', 'Price per Share', 'Type'])

default_csv_text = "Date,Shares,Price per Share,Type\n2024-05-01,100,10.00,Buy\n2024-05-01,50,12.00,Buy\n2024-05-02,30,15.00,Buy\n2024-05-02,120,15.00,Sell"


st.subheader('Enter bulk transactions:')
csv_data = st.text_area("Input your transactions in CSV format (Date, Shares, Price per Share, Type (Buy/Sell))", value=default_csv_text, height=150)
if st.button('Upload Transactions'):
    try:
        data_io = StringIO(csv_data)
        df = pd.read_csv(data_io)
        st.session_state.transactions = pd.concat([st.session_state.transactions, df], ignore_index=True)
        st.success('Transactions uploaded successfully.')
    except Exception as e:
        st.error(f"An error occurred while reading the CSV data: {e}")


def add_transaction(date, shares, price_per_share, transaction_type):
    new_data = pd.DataFrame({
        'Date': [date],
        'Shares': [shares if transaction_type == 'Buy' else -shares],
        'Price per Share': [price_per_share],
        'Type': [transaction_type]
    })
    st.session_state.transactions = pd.concat([st.session_state.transactions, new_data], ignore_index=True)

with st.form("transaction_form"):
    date = st.date_input('Date')
    shares = st.number_input('Shares', min_value=0)
    price_per_share = st.number_input('Price per Share', min_value=0.01, format='%.2f')
    transaction_type = st.radio('Transaction Type:', ('Buy', 'Sell'))
    submitted = st.form_submit_button("Add Transaction")
    if submitted:
        add_transaction(date, shares, price_per_share, transaction_type)
        st.success('Transaction added successfully.')


st.write("Your Transactions:")
st.dataframe(st.session_state.transactions)


cost_method = st.selectbox("Select Cost Calculation Method:", ('Weighted Average', 'FIFO', 'LIFO', 'Compressed FIFO'))

def calculate_costs(transactions, method):
    transactions = transactions.copy()
    if method == 'Weighted Average':
        total_shares = 0
        total_cost = 0
        cost_detail = ""
        for _, transaction in transactions.iterrows():
            if transaction['Type'] == 'Buy':
                
                total_shares += transaction['Shares']
                total_cost += transaction['Shares'] * transaction['Price per Share']
            elif transaction['Type'] == 'Sell':
                
                if total_shares > 0:
                    weighted_average = total_cost / total_shares
                else:
                    weighted_average = 0
                
                
                cost_of_sold_shares = transaction['Shares'] * weighted_average
                
                total_shares -= transaction['Shares']
                total_cost -= cost_of_sold_shares
                
                # Generate details of the calculation for this transaction
                cost_detail += f"After selling {transaction['Shares']} shares:\n"
                cost_detail += f"Cost Basis: Remaining cost basis after sale = {total_cost:.2f}\n"
                cost_detail += f"Average Entry Price: {weighted_average:.2f} per share before sale\n"
                
        
        average_cost = total_cost / total_shares if total_shares > 0 else 0
        cost_detail += f"Final Cost Basis after all transactions = ${total_cost:.2f}\n"
        cost_detail += f"Final Average Entry Price after all transactions = ${average_cost:.2f}"
        return total_cost, average_cost, cost_detail

    elif method == 'FIFO' or method == 'Compressed FIFO':
        if method == 'Compressed FIFO':
            transactions['Date'] = pd.to_datetime(transactions['Date'])
            daily_transactions = transactions.groupby(['Date', 'Type']).apply(
                lambda x: pd.Series({
                    'Shares': x['Shares'].sum(),
                    'Price per Share': (x['Shares'] * x['Price per Share']).sum() / x['Shares'].sum() if x['Shares'].sum() != 0 else 0
                }) if x['Type'].iloc[0] == 'Buy' else pd.Series({'Shares': x['Shares'].sum(), 'Price per Share': 0})
            ).reset_index()
            transactions = daily_transactions
        else:
            transactions['Date'] = pd.to_datetime(transactions['Date'])

        inventory = []
        total_shares = 0
        cost_detail = ""
        for _, transaction in transactions.iterrows():
            if transaction['Type'] == 'Buy':
                inventory.append((transaction['Shares'], transaction['Price per Share']))
                total_shares += transaction['Shares']
            elif transaction['Type'] == 'Sell':
                shares_to_sell = transaction['Shares']
                initial_cost_basis = sum(share * price for share, price in inventory)
                shares_sold_cost = 0
                while shares_to_sell > 0 and inventory:
                    shares, cost = inventory[0]
                    if shares > shares_to_sell:
                        shares_sold_cost += shares_to_sell * cost
                        inventory[0] = (shares - shares_to_sell, cost)
                        total_shares -= shares_to_sell
                        shares_to_sell = 0
                    else:
                        shares_to_sell -= shares
                        shares_sold_cost += shares * cost
                        total_shares -= shares
                        inventory.pop(0)
                final_cost_basis = sum(share * price for share, price in inventory)
                cost_detail += f"Initial Cost Basis: ${initial_cost_basis:.2f} - {transaction['Shares']}*{shares_sold_cost/transaction['Shares']:.2f} = ${final_cost_basis:.2f}\n"
        average_cost = final_cost_basis / total_shares if total_shares > 0 else 0
        cost_detail += f"Average entry price: ${final_cost_basis:.2f}/{total_shares} = ${average_cost:.2f}"
        return final_cost_basis, average_cost, cost_detail

    elif method == 'LIFO':
        inventory = []
        total_shares = 0
        for _, transaction in transactions.iterrows():
            if transaction['Type'] == 'Buy':
                inventory.append((transaction['Shares'], transaction['Price per Share']))
                total_shares += transaction['Shares']
            elif transaction['Type'] == 'Sell':
                shares_to_sell = transaction['Shares']
                while shares_to_sell > 0 and inventory:
                    shares, cost = inventory[-1]
                    if shares > shares_to_sell:
                        inventory[-1] = (shares - shares_to_sell, cost)
                        total_shares -= shares_to_sell
                        shares_to_sell = 0
                    else:
                      
                        shares_to_sell -= shares
                        total_shares -= shares
                        inventory.pop()
        total_cost = sum(share * price for share, price in inventory)
        average_cost = total_cost / total_shares if total_shares > 0 else 0
        return total_cost, average_cost, ""

if not st.session_state.transactions.empty:
    cost_basis, average_cost, detailed_metrics = calculate_costs(st.session_state.transactions, cost_method)
    st.metric(label="Cost Basis", value=f"${cost_basis:.2f}")
    st.metric(label="Average Cost per Share", value=f"${average_cost:.2f}")
    if detailed_metrics:
        st.text(detailed_metrics)




if not st.session_state.transactions.empty:
    delete_index = st.number_input('Enter the index of the transaction to delete', min_value=0, max_value=len(st.session_state.transactions)-1, step=1)
    if st.button('Delete Transaction'):
        st.session_state.transactions = st.session_state.transactions.drop(st.session_state.transactions.index[delete_index]).reset_index(drop=True)
        st.success('Transaction deleted successfully.')

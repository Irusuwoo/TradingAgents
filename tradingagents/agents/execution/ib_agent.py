import functools
import os
from ib_insync import IB, Stock, Order

def create_ib_agent(name: str):
    def ib_agent_node(state, name=None):
        final_decision = state.get("final_trade_decision", "").strip()
        company_name = state.get("company_name", "").upper()

        if not final_decision or not company_name:
            return {"trade_confirmation": "Missing decision or company name."}

        ib = IB()
        try:
            ib.connect(os.getenv("IB_HOST", "127.0.0.1"), int(os.getenv("IB_PORT", 7497)), clientId=int(os.getenv("IB_CLIENT_ID", 1)))
        except Exception as e:
            return {"trade_confirmation": f"Failed to connect to IB: {e}"}

        contract = Stock(company_name, 'SMART', 'USD')
        ib.qualifyContracts(contract)

        trade_confirmation = ""

        if "BUY" in final_decision:
            # Example: Buy 10 shares with a 5% stop-loss
            quantity = 10
            ticker = ib.reqMktData(contract)
            ib.sleep(2)
            market_price = ticker.last
            if market_price:
                stop_loss_price = round(market_price * 0.95, 2)
                take_profit_price = round(market_price * 1.10, 2) # Example 10% take profit

                buy_order = Order(action='BUY', totalQuantity=quantity, orderType='MKT')
                stop_loss_order = Order(action='SELL', totalQuantity=quantity, orderType='STP', auxPrice=stop_loss_price)
                take_profit_order = Order(action='SELL', totalQuantity=quantity, orderType='LMT', lmtPrice=take_profit_price)

                buy_trade = ib.placeOrder(contract, buy_order)
                ib.sleep(1)
                stop_loss_trade = ib.placeOrder(contract, stop_loss_order)
                ib.sleep(1)
                take_profit_trade = ib.placeOrder(contract, take_profit_order)

                trade_confirmation = f"Placed BUY order for {quantity} shares of {company_name} with stop-loss at {stop_loss_price} and take-profit at {take_profit_price}."
            else:
                trade_confirmation = f"Could not retrieve market price for {company_name} to place BUY order."

        elif "SELL" in final_decision:
            # Example: Sell all shares
            position = ib.positions(account=os.getenv("IB_ACCOUNT"))
            quantity_to_sell = 0
            for pos in position:
                if pos.contract.symbol == company_name:
                    quantity_to_sell = pos.position
                    break
            
            if quantity_to_sell > 0:
                sell_order = Order(action='SELL', totalQuantity=quantity_to_sell, orderType='MKT')
                sell_trade = ib.placeOrder(contract, sell_order)
                trade_confirmation = f"Placed SELL order for {quantity_to_sell} shares of {company_name}."
            else:
                trade_confirmation = f"No position found for {company_name} to SELL."

        else: # HOLD
            trade_confirmation = f"Holding position for {company_name}."

        ib.disconnect()
        return {"trade_confirmation": trade_confirmation, "sender": name}

    return ib_agent_node

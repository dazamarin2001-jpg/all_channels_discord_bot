"""Make every /trade category deduct from the account's combined Pending Funds."""

from pathlib import Path


path = Path("legacy_main.py")
if not path.exists():
    print("Trade combined-funds patch warning: legacy_main.py was not found.")
else:
    text = path.read_text(encoding="utf-8")
    marker = "TRADE_PAY_REQUEST_PATCH_VERSION = 4"

    if marker not in text:
        text = text.replace(
            '        label="Donation/Sale",\n'
            '        placeholder="Type Donation or Sale",',
            '        label="Donation/Sale/Pay Request",\n'
            '        placeholder="Type Donation, Sale, or Pay Request",',
            1,
        )

        old_validation = '''            category = clean_text(self.category.value).title()
            if category.casefold() not in {"sale", "donation"}:
                await interaction.followup.send("Donation/Sale must be either `Donation` or `Sale`.", ephemeral=True)
                return'''
        new_validation = '''            category_key = " ".join(
                clean_text(self.category.value).replace("-", " ").split()
            ).casefold()
            if category_key == "payrequest":
                category_key = "pay request"

            category_names = {
                "sale": "Sale",
                "donation": "Donation",
                "pay request": "Pay Request",
            }
            if category_key not in category_names:
                await interaction.followup.send(
                    "Category must be `Donation`, `Sale`, or `Pay Request`.",
                    ephemeral=True,
                )
                return
            category = category_names[category_key]'''

        if old_validation in text:
            text = text.replace(old_validation, new_validation, 1)
        elif new_validation not in text:
            print("Trade combined-funds patch warning: category validation block was not found.")

        old_category_filter = '        if not account_key or category_key not in {"sale", "donation"}:'
        new_category_filter = '        if not account_key or category_key not in {"sale", "donation", "pay request"}:'
        if old_category_filter in text:
            text = text.replace(old_category_filter, new_category_filter, 1)
        elif new_category_filter not in text:
            print("Trade combined-funds patch warning: completed-trade category filter was not found.")

        original_pending_math = '''        sales_traded = traded_out.get((account_key, "sale"), 0.0)
        donations_traded = traded_out.get((account_key, "donation"), 0.0)
        pending_sales = max(0.0, sales_total - sales_traded)
        pending_donations = max(0.0, donations_total - donations_traded)
        total_traded = sales_traded + donations_traded
        pending_funds = pending_sales + pending_donations'''

        version3_pending_math = '''        sales_traded = traded_out.get((account_key, "sale"), 0.0)
        donations_traded = traded_out.get((account_key, "donation"), 0.0)
        pay_requested = traded_out.get((account_key, "pay request"), 0.0)
        pending_sales = max(0.0, sales_total - sales_traded)
        pending_donations = max(0.0, donations_total - donations_traded)
        total_traded = sales_traded + donations_traded + pay_requested
        pending_funds = max(0.0, pending_sales + pending_donations - pay_requested)'''

        combined_pending_math = '''        sales_traded = traded_out.get((account_key, "sale"), 0.0)
        donations_traded = traded_out.get((account_key, "donation"), 0.0)
        pay_requested = traded_out.get((account_key, "pay request"), 0.0)
        pending_sales = max(0.0, sales_total - sales_traded)
        pending_donations = max(0.0, donations_total - donations_traded)
        total_traded = sales_traded + donations_traded + pay_requested
        pending_funds = max(0.0, sales_total + donations_total - total_traded)'''

        if version3_pending_math in text:
            text = text.replace(version3_pending_math, combined_pending_math, 1)
        elif original_pending_math in text:
            text = text.replace(original_pending_math, combined_pending_math, 1)
        elif combined_pending_math not in text:
            print("Trade combined-funds patch warning: pending-funds calculation block was not found.")

        original_balance_selector = '''    category_key = category.casefold()
    balance_index = 8 if category_key == "donation" else 7
    balance_col = "I" if category_key == "donation" else "H"'''

        version3_balance_selector = '''    category_key = category.casefold()
    if category_key == "pay request":
        balance_index = 10
        balance_col = "K"
    elif category_key == "donation":
        balance_index = 8
        balance_col = "I"
    else:
        balance_index = 7
        balance_col = "H"'''

        combined_balance_selector = '''    category_key = category.casefold()
    balance_index = 10
    balance_col = "K"'''

        if version3_balance_selector in text:
            text = text.replace(version3_balance_selector, combined_balance_selector, 1)
        elif original_balance_selector in text:
            text = text.replace(original_balance_selector, combined_balance_selector, 1)
        elif combined_balance_selector not in text:
            print("Trade combined-funds patch warning: trade balance selector was not found.")

        category_error = 'raise RuntimeError(f"{account} only has {format_credits(current_balance)} available in {category} funds.")'
        pending_error = 'raise RuntimeError(f"{account} only has {format_credits(current_balance)} available in Pending Funds.")'
        if category_error in text:
            text = text.replace(category_error, pending_error, 1)
        elif pending_error not in text:
            print("Trade combined-funds patch warning: insufficient-balance error was not found.")

        version2_flow = '''            if category == "Pay Request":
                # Pay Requests are logged for tracking but do not reduce a seller's
                # pending Sale or Donation balance.
                old_balance = "N/A"
                new_balance = "N/A"
            else:
                _balance_col, old_balance, new_balance = await asyncio.to_thread(
                    apply_trade_to_sales_summary,
                    account,
                    category,
                    amount_value,
                )

            await asyncio.to_thread(
                append_trade_to_summary_log,
                [account, category, "Trade Out", negative_change, traded_to, "Completed"],
            )
            if "refresh_pending_balances" in globals():
                await asyncio.to_thread(refresh_pending_balances)'''

        old_flow_with_refresh = '''            _balance_col, old_balance, new_balance = await asyncio.to_thread(apply_trade_to_sales_summary, account, category, amount_value)
            await asyncio.to_thread(
                append_trade_to_summary_log,
                [account, category, "Trade Out", negative_change, traded_to, "Completed"],
            )
            await asyncio.to_thread(refresh_pending_balances)'''

        old_flow_without_refresh = '''            _balance_col, old_balance, new_balance = await asyncio.to_thread(apply_trade_to_sales_summary, account, category, amount_value)
            await asyncio.to_thread(
                append_trade_to_summary_log,
                [account, category, "Trade Out", negative_change, traded_to, "Completed"],
            )'''

        combined_flow = '''            _balance_col, old_balance, new_balance = await asyncio.to_thread(
                apply_trade_to_sales_summary,
                account,
                category,
                amount_value,
            )
            await asyncio.to_thread(
                append_trade_to_summary_log,
                [account, category, "Trade Out", negative_change, traded_to, "Completed"],
            )
            if "refresh_pending_balances" in globals():
                await asyncio.to_thread(refresh_pending_balances)'''

        if version2_flow in text:
            text = text.replace(version2_flow, combined_flow, 1)
        elif old_flow_with_refresh in text:
            text = text.replace(old_flow_with_refresh, combined_flow, 1)
        elif old_flow_without_refresh in text:
            text = text.replace(old_flow_without_refresh, combined_flow, 1)
        elif combined_flow not in text:
            print("Trade combined-funds patch warning: trade submission flow was not found.")

        version2_balance_fields = '''            embed.add_field(
                name="Previous Category Balance",
                value="N/A" if category == "Pay Request" else old_balance,
                inline=True,
            )
            embed.add_field(
                name="New Category Balance",
                value="N/A" if category == "Pay Request" else new_balance,
                inline=True,
            )'''

        original_balance_fields = '''            embed.add_field(name="Previous Category Balance", value=old_balance, inline=True)
            embed.add_field(name="New Category Balance", value=new_balance, inline=True)'''

        version3_balance_fields = '''            balance_name = "Pending Funds" if category == "Pay Request" else "Category Balance"
            embed.add_field(name=f"Previous {balance_name}", value=old_balance, inline=True)
            embed.add_field(name=f"New {balance_name}", value=new_balance, inline=True)'''

        combined_balance_fields = '''            embed.add_field(name="Previous Pending Funds", value=old_balance, inline=True)
            embed.add_field(name="New Pending Funds", value=new_balance, inline=True)'''

        if version3_balance_fields in text:
            text = text.replace(version3_balance_fields, combined_balance_fields, 1)
        elif version2_balance_fields in text:
            text = text.replace(version2_balance_fields, combined_balance_fields, 1)
        elif original_balance_fields in text:
            text = text.replace(original_balance_fields, combined_balance_fields, 1)
        elif combined_balance_fields not in text:
            print("Trade combined-funds patch warning: balance embed fields were not found.")

        version2_footer = '''            if category == "Pay Request":
                embed.set_footer(
                    text="Logged to Summary Log. Pay Requests do not change Sale or Donation balances."
                )
            else:
                embed.set_footer(text="Logged to Summary Log and applied to /sale summary totals.")'''

        version3_footer = '''            if category == "Pay Request":
                embed.set_footer(
                    text="Logged to Summary Log and deducted from total Pending Funds."
                )
            else:
                embed.set_footer(text="Logged to Summary Log and applied to /sale summary totals.")'''

        original_footer = '            embed.set_footer(text="Logged to Summary Log and applied to /sale summary totals.")'
        combined_footer = '            embed.set_footer(text="Logged to Summary Log and deducted from total Pending Funds.")'

        if version3_footer in text:
            text = text.replace(version3_footer, combined_footer, 1)
        elif version2_footer in text:
            text = text.replace(version2_footer, combined_footer, 1)
        elif original_footer in text:
            text = text.replace(original_footer, combined_footer, 1)
        elif combined_footer not in text:
            print("Trade combined-funds patch warning: trade embed footer was not found.")

        constants_anchor = 'TRADE_ALLOWED_ROLE_NAMES = {"rank sellers", "rank seller", "chat moderator"}\n'
        if marker not in text:
            if constants_anchor in text:
                text = text.replace(constants_anchor, constants_anchor + marker + "\n", 1)
            else:
                print("Trade combined-funds patch warning: constants anchor was not found.")

        path.write_text(text, encoding="utf-8")
        print("Trade combined Pending Funds patch version 4 applied.")
    else:
        print("Trade combined Pending Funds patch version 4 already applied.")

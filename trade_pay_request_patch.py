"""Allow /trade to accept Pay Request without changing sale or donation balances."""

from pathlib import Path


path = Path("legacy_main.py")
if not path.exists():
    print("Trade Pay Request patch warning: legacy_main.py was not found.")
else:
    text = path.read_text(encoding="utf-8")
    marker = "TRADE_PAY_REQUEST_PATCH_VERSION = 1"

    if marker not in text:
        constants_anchor = 'TRADE_ALLOWED_ROLE_NAMES = {"rank sellers", "rank seller", "chat moderator"}\n'
        if constants_anchor in text:
            text = text.replace(
                constants_anchor,
                constants_anchor + marker + "\n",
                1,
            )
        else:
            print("Trade Pay Request patch warning: constants anchor was not found.")

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
            print("Trade Pay Request patch warning: category validation block was not found.")

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
        new_flow = '''            if category == "Pay Request":
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

        if old_flow_with_refresh in text:
            text = text.replace(old_flow_with_refresh, new_flow, 1)
        elif old_flow_without_refresh in text:
            text = text.replace(old_flow_without_refresh, new_flow, 1)
        elif new_flow not in text:
            print("Trade Pay Request patch warning: trade submission flow was not found.")

        old_footer = '            embed.set_footer(text="Logged to Summary Log and applied to /sale summary totals.")'
        new_footer = '''            if category == "Pay Request":
                embed.set_footer(
                    text="Logged to Summary Log. Pay Requests do not change Sale or Donation balances."
                )
            else:
                embed.set_footer(text="Logged to Summary Log and applied to /sale summary totals.")'''
        if old_footer in text:
            text = text.replace(old_footer, new_footer, 1)
        elif new_footer not in text:
            print("Trade Pay Request patch warning: trade embed footer was not found.")

        path.write_text(text, encoding="utf-8")
        print("Trade Pay Request support patch applied.")
    else:
        print("Trade Pay Request support patch already applied.")

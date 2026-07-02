"""Small startup patch for Discord slash command names.

Python automatically imports this file on startup when it is present on sys.path.
It lets us rename slash commands without rewriting the large bot.py file.
"""

try:
    from discord import app_commands

    _original_command_init = app_commands.Command.__init__
    _original_sync = app_commands.CommandTree.sync

    def _patched_command_init(self, *args, **kwargs):
        if kwargs.get("name") == "rank-sale":
            kwargs["name"] = "sale"
        elif kwargs.get("name") == "rank-sale-summary":
            kwargs["name"] = "sales-summary"
        return _original_command_init(self, *args, **kwargs)

    async def _patched_sync(self, *args, **kwargs):
        # If a flat /rank-sale-summary command exists, convert it to /sales summary before syncing.
        try:
            existing = list(self.get_commands())
            summary_cmd = next((cmd for cmd in existing if cmd.name in {"rank-sale-summary", "sales-summary"}), None)

            if summary_cmd is not None:
                for command_name in ("rank-sale-summary", "sales-summary", "sales"):
                    try:
                        self.remove_command(command_name)
                    except Exception:
                        pass

                try:
                    summary_cmd._name = "summary"
                except Exception:
                    pass

                sales_group = app_commands.Group(name="sales", description="Sales commands")
                sales_group.add_command(summary_cmd)
                self.add_command(sales_group)
        except Exception:
            pass

        return await _original_sync(self, *args, **kwargs)

    app_commands.Command.__init__ = _patched_command_init
    app_commands.CommandTree.sync = _patched_sync
except Exception:
    # Never block the bot from starting if this compatibility patch cannot load.
    pass

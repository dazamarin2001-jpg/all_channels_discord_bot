"""Startup patch for Discord slash command names.

Python imports sitecustomize automatically on startup when this file is on sys.path.
This patch renames slash commands before the bot syncs them to Discord.
"""

try:
    from discord import app_commands

    print("Slash command rename patch loaded.")

    _original_tree_command = app_commands.CommandTree.command
    _original_command_init = app_commands.Command.__init__
    _original_sync = app_commands.CommandTree.sync

    def _rename_command_name(name):
        if name == "rank-sale":
            return "sale"
        if name == "rank-sale-summary":
            return "sales-summary"
        return name

    def _patched_tree_command(self, *args, **kwargs):
        if "name" in kwargs:
            kwargs["name"] = _rename_command_name(kwargs["name"])
        return _original_tree_command(self, *args, **kwargs)

    def _patched_command_init(self, *args, **kwargs):
        if "name" in kwargs:
            kwargs["name"] = _rename_command_name(kwargs["name"])
        return _original_command_init(self, *args, **kwargs)

    async def _patched_sync(self, *args, **kwargs):
        try:
            existing = list(self.get_commands())

            # Convert a flat summary command into a grouped command: /sales summary
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

            print("Syncing slash commands:", [cmd.name for cmd in self.get_commands()])
        except Exception as exc:
            print(f"Slash command rename patch warning: {type(exc).__name__}: {exc}")

        return await _original_sync(self, *args, **kwargs)

    app_commands.CommandTree.command = _patched_tree_command
    app_commands.Command.__init__ = _patched_command_init
    app_commands.CommandTree.sync = _patched_sync
except Exception as exc:
    print(f"Slash command rename patch failed to load: {type(exc).__name__}: {exc}")
